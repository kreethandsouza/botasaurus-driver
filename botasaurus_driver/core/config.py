import tempfile
import os
import sys
from ..driver_utils import convert_to_absolute_profile_path
from .env import is_vmish, is_docker


def temp_profile_dir(port, parent_folder="bota"):
    """
    Creates a unique subfolder under the specified parent folder within the system's temporary directory.
    If the parent folder does not exist, it will be created.

    Returns the path to the created unique subfolder.
    """
    temp_dir = tempfile.gettempdir()
    parent_path = os.path.join(temp_dir, parent_folder)
    os.makedirs(parent_path, exist_ok=True)

    unique_folder = os.path.normpath(tempfile.mkdtemp(prefix=port, dir=parent_path))
    return unique_folder


__all__ = [
    "Config",
    "find_chrome_executable",
    "temp_profile_dir",
    "is_posix",
    "PathLike",
]


is_posix = sys.platform.startswith(("darwin", "cygwin", "linux", "linux2"))

PathLike = str
AUTO = None


def free_port() -> int:
    """
    Determines a free port using sockets.
    """
    import socket

    free_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    free_socket.bind(("127.0.0.1", 0))
    free_socket.listen(5)
    port: int = free_socket.getsockname()[1]
    free_socket.close()
    return port

def clean_profile(profile):
            if profile:
                return str(profile).strip()

def should_force_headless():
    return is_vmish

def should_force_no_sandbox():
    return is_docker

def unique_keys(all_urls):
    return list(dict.fromkeys(all_urls))

def create_local_proxy(auth_proxy):
    from botasaurus_proxy_authentication import create_proxy
    return create_proxy(auth_proxy)

def close_local_proxy(local_proxy):
    from botasaurus_proxy_authentication import close_proxy
    return close_proxy(local_proxy)

def create_extensions_string(extensions):
            if not isinstance(extensions, list):
                extensions = [extensions]
            extensions_str = ",".join(
                [
                    extension.load(with_command_line_option=False)
                    for extension in extensions
                ]
            )
            return "--load-extension=" + extensions_str

def add_essential_options(options, profile, window_size, user_agent):
    if window_size and window_size != "REAL":
        from ..window_size import WindowSizeInstance, WindowSize

        if window_size == WindowSize.RANDOM:
            window_size = WindowSizeInstance.get_random()
        elif window_size == WindowSize.HASHED:
            window_size = WindowSizeInstance.get_hashed(profile)
        else:
            window_size = window_size

        window_size = WindowSize.window_size_to_string(window_size)
        options.add_argument(f"--window-size={window_size}")

    if user_agent and user_agent != "REAL":
        from ..user_agent import UserAgentInstance, UserAgent

        if user_agent == UserAgent.RANDOM:
            user_agent = UserAgentInstance.get_random()
        elif user_agent == UserAgent.HASHED:
            user_agent = UserAgentInstance.get_hashed(profile)
        else:
            user_agent = user_agent

        options.add_argument(f'--user-agent={user_agent}')

class Config:
    """
    Config object
    """

    def __init__(
        self,
        headless=False,
        proxy=None,
        profile=None,
        tiny_profile=False,
        block_images=False,
        block_images_and_css=False,
        wait_for_complete_page_load=False,
        extensions=[],
        arguments=[],
        user_agent=None,
        window_size=None,
        lang=None,
        beep=False,
    ):
        if tiny_profile and profile is None:
            raise ValueError('Profile must be given when using tiny profile')

        self.headless=headless
        self.proxy=proxy

        if self.proxy:
            self.local_proxy = create_local_proxy(self.proxy)
        else:
            self.local_proxy = None

        self.profile=clean_profile(profile)
        self.tiny_profile=tiny_profile

        self.block_images=block_images
        self.block_images_and_css=block_images_and_css

        self.wait_for_complete_page_load=wait_for_complete_page_load

        self.extensions=extensions

        self.arguments=arguments

        self.user_agent=user_agent
        self.window_size=window_size

        self.lang=lang
        self.beep=beep

        self.host = "127.0.0.1"
        self.port = free_port()
        

        if self.tiny_profile or not self.profile:
            self.profile_directory = temp_profile_dir(str(self.port) + "_")
            self.is_temporary_profile = True
        else:
            self.profile_directory = convert_to_absolute_profile_path(self.profile)
            self.is_temporary_profile = False


        self.arguments = arguments

        self.browser_executable_path = find_chrome_executable()

        self.autodiscover_targets = True
        
        # Botasaurus Retry Data
        self.is_new = True
        
        self.retry_attempt = 0
        self.is_retry = False
        self.is_last_retry = False

        add_essential_options(self, self.profile, self.window_size, self.user_agent)

        # other keyword args will be accessible by attribute
        super().__init__()
        self.default_arguments = [
            "--start-maximized",
            "--no-first-run",
            "--disable-site-isolation-trials",
            "--disable-backgrounding-occluded-windows",
            "--disable-hang-monitor",
            "--metrics-recording-only",
            "--disable-sync",
            "--disable-background-timer-throttling",
            "--disable-prompt-on-repost",
            "--disable-background-networking",
            "--disable-infobars",
            "--remote-allow-origins=*",
            "--homepage=about:blank",
            "--no-service-autorun",
            "--disable-ipc-flooding-protection",
            "--disable-session-crashed-bubble",
            "--force-fieldtrials=*BackgroundTracing/default/",
            "--disable-breakpad",
            "--password-store=basic",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-client-side-phishing-detection",
            "--use-mock-keychain",
            "--no-pings",
            "--disable-renderer-backgrounding",
            "--disable-component-update",
            "--disable-dev-shm-usage",
            "--disable-default-apps",
            "--disable-domain-reliability",
            "--no-default-browser-check",
        ]

    @property
    def browser_args(self):
        return sorted(self.default_arguments + self.arguments)

    def close(self):
        if self.local_proxy:
            close_local_proxy(self.local_proxy)


    def __getattr__(self, item):
        if item not in self.__dict__:
            return

    def __call__(self):
        args = self.default_arguments
        args.append ("--user-data-dir=%s" % self.profile_directory)

        if self.arguments:
            args.extend(self.arguments)
        
        if self.headless or should_force_headless():
            args.append("--headless=new")

        if should_force_no_sandbox():
            args.append("--no-sandbox")

        if self.host:
            args.append("--remote-debugging-host=%s" % self.host)

        if self.port:
            args.append("--remote-debugging-port=%s" % self.port)

        if self.lang:
            args.append(f'--lang={self.lang}')

        if self.extensions:
            args.append(create_extensions_string(self.extensions))

        if self.local_proxy:
            args.append(f'--proxy-server=' + self.local_proxy)

        args = unique_keys(args)
        return args

    def add_argument(self, arg: str):
       
        self.arguments.append(arg)

    def __repr__(self):
        s = f"{self.__class__.__name__}"
        for k, v in ({**self.__dict__, **self.__class__.__dict__}).items():
            if k[0] == "_":
                continue
            if not v:
                continue
            if isinstance(v, property):
                v = getattr(self, k)
            if callable(v):
                continue
            s += f"\n\t{k} = {v}"
        return s

    #     d = self.__dict__.copy()
    #     d.pop("browser_args")
    #     d["browser_args"] = self()
    #     return d



def find_chrome_executable(return_all=False):
    """
    Finds the chrome, beta, canary, chromium executable
    and returns the disk path
    """
    candidates = []
    if is_posix:
        for item in os.environ.get("PATH").split(os.pathsep):
            for subitem in (
                "google-chrome",
                "chromium",
                "chromium-browser",
                "chrome",
                "google-chrome-stable",
            ):
                candidates.append(os.sep.join((item, subitem)))
        if "darwin" in sys.platform:
            candidates += [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
            ]

    else:
        for item in map(
            os.environ.get,
            ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA", "PROGRAMW6432"),
        ):
            if item is not None:
                for subitem in (
                    "Google/Chrome/Application",
                    "Google/Chrome Beta/Application",
                    "Google/Chrome Canary/Application",
                ):
                    candidates.append(os.sep.join((item, subitem, "chrome.exe")))
    rv = []
    for candidate in candidates:
        if os.path.exists(candidate) and os.access(candidate, os.X_OK):
            rv.append(candidate)
        else:
            pass

    winner = None

    if return_all and rv:
        return rv

    if rv and len(rv) > 1:
        # assuming the shortest path wins
        winner = min(rv, key=lambda x: len(x))

    elif len(rv) == 1:
        winner = rv[0]

    if winner:
        return os.path.normpath(winner)

    raise FileNotFoundError(
        "could not find a valid chrome browser binary. please make sure chrome is installed."
    )