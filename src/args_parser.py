import argparse


def parse_args() -> argparse.Namespace:
    """
    аргументы, передаваемые через терминал
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--coef_period",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--month_number", required=True, type=int, help="serial number of the month"
    )
    return parser.parse_args()
