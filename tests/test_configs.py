from aioworkers_kafka.configs import flat_conf


def test_flat_conf():
    conf = {
        "a": 1,
        "b": {
            "c": 2,
            "d": {
                "e": 3,
            },
        },
    }
    assert flat_conf(conf) == {
        "a": 1,
        "b.c": 2,
        "b.d.e": 3,
    }
