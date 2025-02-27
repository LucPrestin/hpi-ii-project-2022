import click

from announcement import State
from crawlers import \
    crawl_lobby_register_entries, \
    crawl_lobby_institution_with_id, \
    crawl_trade_register_announcements


@click.group()
def cli():
    pass


@cli.group('lobby_register')
def lobby_register():
    pass


@lobby_register.command('crawl_all')
def crawl_lobby_register() -> None:
    crawl_lobby_register_entries()


@lobby_register.command('crawl_institution')
@click.option('-i', '--id', 'register_number', type=click.STRING,
              help='The lobby register number/id for the entry to crawl')
def crawl_lobby_institution(register_number: str) -> None:
    crawl_lobby_institution_with_id(register_number)


@cli.group('trade_register')
def trade_register():
    pass


@trade_register.command('crawl')
@click.option("-i", "--id", "announcement_id", type=int, help="The announcement_id to initialize the crawl from")
@click.option("-s", "--state", type=click.Choice(State), help="The state ISO code")
def crawl_trade_register(announcement_id: int, state: State) -> None:
    crawl_trade_register_announcements(announcement_id, state)


if __name__ == '__main__':
    cli()
