import json
import pathlib

import allure
from jsonschema import Draft4Validator

SCHEMAS = "./integration/tests/tracer/schemas/"


def get_schema(file_name):
    with open(pathlib.Path(SCHEMAS, file_name)) as f:
        d = json.load(f)
        return d


@allure.step("Validate debug_traceCall response by json scheme ")
def validate_response_result(response):
    schema = get_schema("debug_traceCall.json")
    validator = Draft4Validator(schema)
    assert validator.is_valid(response["result"])
