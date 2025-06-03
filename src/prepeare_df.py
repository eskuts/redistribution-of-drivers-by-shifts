import os

import pandas as pd
from dotenv import load_dotenv

from src.args_parser import parse_args

load_dotenv()
args = parse_args()


def assign_column(colons_by_date, row):
    """определение колонны по дате, наряду и маршурту"""

    colons_by_date["Дата"] = pd.to_datetime(colons_by_date["Дата"])

    # Находим соответствующие строки в таблице 2
    matching_rows = colons_by_date["Маршрут"] == row["Маршрут"]
    matching_table = colons_by_date.loc[matching_rows]

    sorted_matching_table = matching_table.sort_values(by="Дата", ascending=False)

    for date in sorted_matching_table["Дата"]:
        if row["Дата"] >= date:
            wanted_date = date
            break

    wanted_table = sorted_matching_table[sorted_matching_table["Дата"] == wanted_date]

    # сортируем мэтчинг_тэйбл по дате в обратном порядке, выбираем нужную дату, потом уже смотрим, там одна стргка или две
    # Если длина найденной таблицы равна 1, присваиваем значение колонны
    if len(wanted_table) == 1:
        row["Колонна"] = wanted_table["Колонна"].iloc[0]
        row["Филиал"] = wanted_table["Филиал"].iloc[0]
        return row
    # Если длина равна 2, ищем в какой строке в столбце "список_нарядов" содержится row['наряд'] и присваиваем значение колонны
    elif len(wanted_table) == 2:
        for index, row_table2 in wanted_table.iterrows():
            if row["Наряд"] in row_table2["Наряд"]:
                row["Колонна"] = row_table2["Колонна"]
                row["Филиал"] = row_table2["Филиал"]
                return row
            else:
                continue

    return 0


def assign_distances(excel_df, dists):
    # Преобразование дат в формат datetime
    excel_df["Дата"] = pd.to_datetime(
        excel_df["Дата"], format="%d.%m.%Y", errors="coerce"
    )
    dists["Дата"] = pd.to_datetime(dists["Дата"], format="%d.%m.%Y", errors="coerce")

    # Группировка и сортировка
    grouped = excel_df.groupby(["Дата", "Маршрут", "Направление"])
    sorted_dists = dists.sort_values(by=["Маршрут", "Дата"], ascending=[False, False])

    distances_dict = {}

    for group_key, group_data in grouped:
        date_event, route, direction = group_key
        route_dists = sorted_dists[sorted_dists["Маршрут"] == route]

        # Поиск ближайшей даты
        matching_row = route_dists[route_dists["Дата"] <= date_event].head(1)

        if not matching_row.empty:
            distance = (
                matching_row.iloc[0]["от НП"]
                if direction in ["от НП", "Прямое", "НП"]
                else matching_row.iloc[0]["от КП"]
            )
            for idx in group_data.index:
                distances_dict[idx] = distance

    excel_df["Дист"] = excel_df.index.map(distances_dict)
    return excel_df


def add_coefficients(
    acts_data: pd.DataFrame, coefficient_period: str, coefs
) -> pd.DataFrame:
    """в зависимости от маршрута и этапа определяется коэффициент"""
    coefs["Маршрут"] = coefs["Маршрут"].astype(str).str.upper()
    coefs_for_period = coefs[["Маршрут", coefficient_period]]
    coefs_for_period = coefs_for_period.rename(columns={coefficient_period: "Коэф"})
    return acts_data.merge(coefs_for_period, on="Маршрут", how="left")


def replace_drivers(group):
    """данные в оригинальной таблице по рейсам, а  не по сменам, в случае замены водителя неверно определяется рейс"""
    # Если хотя бы один водитель NaN, заменяем всех водителей в группе на NaN
    if group["Водитель"].isnull().any():
        group["Водитель"] = "б/в"
    else:
        # В остальных случаях оставляем водителя первого рейса в смене
        group["Водитель"] = group["Водитель"].iloc[0]
    return group


def prepeare_df(excel_df, coefficient_period):
    excel_df = excel_df[
        [
            "Маршрут",
            "Дата",
            "Наряд",
            "Направление",
            "Source.Name",
            "Смена",
            "ТС",
            "Водитель",
            "Причина",
        ]
    ]

    excel_df["Причина"] = excel_df["Причина"].replace(r"(?i)\s*р/с.*", None, regex=True)
    excel_df["Маршрут"] = excel_df["Маршрут"].astype(str)
    excel_df["Водитель"] = excel_df["Водитель"].astype(str)

    dists = pd.read_excel(os.environ[r"DISTS"])
    excel_df = assign_distances(excel_df, dists)

    df_cap = pd.read_excel(os.environ[r"CAPACITIES"], header=None)
    df_cap[0] = df_cap[0].astype(str)
    cap_dict = dict(zip(df_cap[0], df_cap[1]))
    excel_df["Вмест"] = excel_df["Маршрут"].map(cap_dict)

    coefs = pd.read_excel(os.environ[r"COEFS"], sheet_name="Sheet1")
    excel_df = add_coefficients(excel_df, coefficient_period, coefs)

    # строки 304-320 закомменчены, тк больше всего времени занимает обработка оригинального дф, это достоаточно сделать 1 раз

    colons_by_date = pd.read_excel(os.environ[r"ROUTE_DISTR"])

    colons_by_date["Наряд"] = colons_by_date["Наряд"].apply(
        lambda x: list(map(int, x.split(","))) if isinstance(x, str) else x
    )
    excel_df["Стоимость"] = excel_df["Дист"] * excel_df["Вмест"] * excel_df["Коэф"]

    new_df = excel_df.apply(lambda x: assign_column(colons_by_date, x), axis=1)
    new_df["Стоимость"] = new_df["Дист"] * new_df["Вмест"] * new_df["Коэф"]

    new_df["Дата"] = new_df["Дата"].astype(str)

    new_df = new_df.groupby(["Дата", "Маршрут", "Наряд", "Смена"], as_index=False)

    new_df = new_df.apply(replace_drivers)

    grouped_df = new_df.groupby(
        ["Дата", "Маршрут", "Наряд", "Смена", "Водитель", "Колонна", "Филиал"],
        as_index=False,
    ).sum()

    return grouped_df
