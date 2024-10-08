import json
import pathlib


def pytest_collection_modifyitems(config, items):
    deselected_items = []
    selected_items = []
    deselected_marks = []
    network_name = config.getoption("--network")

    if network_name == "geth":
        return

    if network_name == "devnet":
        deselected_marks.append("only_stands")
    else:
        deselected_marks.append("only_devnet")

    envs_file = config.getoption("--envs")
    with open(pathlib.Path().parent.parent / envs_file, "r+") as f:
        environments = json.load(f)

    if len(environments[network_name]["network_ids"]) == 1:
        deselected_marks.append("multipletokens")

    config.hook.pytest_deselected(items=deselected_items)
    items[:] = selected_items
