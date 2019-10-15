from decouple import Csv, config as _config, undefined


def config(option: str, default=undefined, *args, **kwargs):
    if "split" in kwargs:
        kwargs.pop("split")
        kwargs["cast"] = Csv()

    if default is not undefined and default is not None:
        kwargs.setdefault("cast", type(default))
    return _config(option, default=default, *args, **kwargs)
