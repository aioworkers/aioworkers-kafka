from typing import Mapping, Union


def flat_conf(conf: Mapping) -> Mapping[str, Union[int, float, str]]:
    result = {}
    for key, value in conf.items():
        if isinstance(value, Mapping):
            for k, v in flat_conf(value).items():
                result[f"{key}.{k}"] = v
        else:
            result[key] = value
    return result
