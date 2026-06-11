_VALID_PROFILE_KEYS = {"format", "width", "height", "scale", "validate", "engine"}


class _Defaults(object):
    """
    Class to store default settings for image generation.
    """

    def __init__(self):
        self.default_format = "png"
        self.default_width = 700
        self.default_height = 500
        self.default_scale = 1
        self.mathjax = None
        self.topojson = None
        self.plotlyjs = None
        self.headers = {"X-Requested-With": "plotly.py"}
        self.profiles = {
            "web": {"format": "png", "width": 800, "height": 600, "scale": 1},
            "print": {"format": "pdf", "width": 700, "height": 500, "scale": 2},
            "retina": {"format": "png", "width": 700, "height": 500, "scale": 2},
            "thumbnail": {"format": "png", "width": 200, "height": 150, "scale": 1},
        }

    def get_profile(self, name):
        if not isinstance(name, str):
            raise ValueError(
                f"Profile name must be a string, got {type(name).__name__}."
            )
        profile = self.profiles.get(name)
        if profile is None:
            available = sorted(self.profiles.keys())
            raise ValueError(
                f"Export profile {name!r} not found. "
                f"Available profiles: {available}"
            )
        invalid_keys = set(profile.keys()) - _VALID_PROFILE_KEYS
        if invalid_keys:
            raise ValueError(
                f"Profile {name!r} contains invalid keys: {sorted(invalid_keys)}. "
                f"Valid keys are: {sorted(_VALID_PROFILE_KEYS)}"
            )
        return dict(profile)


defaults = _Defaults()
