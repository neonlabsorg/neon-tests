#!/usr/bin/env python3
import click
import importlib


@click.group()
def cli():
    pass


def lazy_command(module_name: str, attr_name: str, cmd_name: str = None):
    """Ленивая регистрация click команды или группы (не импортирует модуль до вызова)"""  # todo

    def load():
        mod = importlib.import_module(module_name)
        return getattr(mod, attr_name)

    class LazyGroup(click.Group):
        def get_command(self, ctx, cmd_name_):
            return load().get_command(ctx, cmd_name_)

        def list_commands(self, ctx):
            return load().list_commands(ctx)

        def invoke(self, ctx):
            return load().invoke(ctx)

        def get_help(self, ctx):
            return load().get_help(ctx)

    class LazyCommand(click.Command):
        def invoke(self, ctx):
            return load().invoke(ctx)

        def get_help(self, ctx):
            return load().get_help(ctx)

    # 💡 Make a wrap instead import
    def resolve_type():
        try:
            mod = importlib.import_module(module_name)
            obj = getattr(mod, attr_name)
            return isinstance(obj, click.Group)
        except Exception:
            return False

    if resolve_type():
        return LazyGroup(name=cmd_name or attr_name)
    else:
        return LazyCommand(name=cmd_name or attr_name)


cli.add_command(lazy_command("cli.commands.allure", "allure_cli"), name="allure")
cli.add_command(lazy_command("cli.commands.slack", "send_notification"), name="send_notification")
cli.add_command(lazy_command("cli.commands.infra", "infra"), name="infra")
cli.add_command(lazy_command("cli.commands.dapps", "dapps"), name="dapps")

cli.add_command(lazy_command("cli.commands.common", "oz"), name="oz")
cli.add_command(lazy_command("cli.commands.common", "run"), name="run")
cli.add_command(lazy_command("cli.commands.common", "requirements"), name="requirements")

cli.add_command(lazy_command("cli.commands.load", "locust"), name="locust")
cli.add_command(lazy_command("cli.commands.load", "k6"), name="k6")

if __name__ == "__main__":
    cli()
