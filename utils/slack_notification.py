import pydantic
from slack_sdk.models.blocks import (
    Block,
    SectionBlock,
    DividerBlock,
    ButtonElement,
    OverflowMenuElement,
    PlainTextObject,
    MarkdownTextObject,
    Option,
)

from utils.types import TestGroup


class SlackNotification(pydantic.BaseModel):
    blocks: list[dict] = []

    def add_block(self, block: Block):
        self.blocks.append(block.to_dict())

    def _add_2_column_block(self, col_1: str, col_2: str):
        block = SectionBlock(
            fields=[
                MarkdownTextObject(text=f"*{col_1}*"),
                MarkdownTextObject(text=col_2),
            ]
        )
        self.add_block(block)

    def add_build_info(self, id_: str, url: str):
        return self._add_2_column_block(col_1="Build", col_2=f"<{url}|`{id_}`>")

    def add_network(self, network: str):
        return self._add_2_column_block(col_1="Network", col_2=network)

    def add_failed_tests(self, tests: dict[TestGroup, int]):
        bullet = "• " if len(tests) > 1 else ""
        test_list = "\n".join(f"{bullet}{group}: {count}" for group, count in tests.items())
        return self._add_2_column_block(col_1="Failed Tests", col_2=test_list)

    def add_failed_test_group(self, test_group: str):
        return self._add_2_column_block(col_1="Failed Tests", col_2=test_group)

    def add_allure_report_url(self, url: str):
        block = SectionBlock(
            text=MarkdownTextObject(text="*Allure report*"),
            accessory=ButtonElement(
                text=PlainTextObject(text="View"),
                url=url,
            )
        )
        self.add_block(block)

    def add_failed_test_names(
            self,
            names: list[str],
            name_length_limit: int = 30,
            limit: int = 10,
    ):
        options = []

        for i, name in enumerate(names):
            if len(name.strip()) == 0:
                continue

            text = name if len(name) <= name_length_limit else f"...{name[-name_length_limit + 3:]}"
            option = Option(
                text=PlainTextObject(text=text),
                value=f"value-{i}",
            )
            options.append(option)

            if i >= limit:
                three_dots = Option(
                    text=PlainTextObject(text="..."),
                    value=f"value-{i + 1}",
                )
                options.append(three_dots)
                break

        if options:
            block = SectionBlock(
                text=MarkdownTextObject(text="*Failed tests details*"),
                accessory=OverflowMenuElement(options=options)
            )

            self.add_block(block)

    def add_comment(self, text: str):
        return self._add_2_column_block(col_1="Comment", col_2=text)

    def add_divider(self):
        block = DividerBlock()
        self.add_block(block)
