import os

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

from src.args_parser import parse_args
from src.consts import months
from src.prepeare_df import prepeare_df


def schedule_drivers(df, driver_routes, group_criterion):
    results = []

    # Проходим по уникальным дням и отделам
    for (day, department), group in df.groupby(["Дата", group_criterion]):
        shifts = group[["Маршрут", "Наряд", "Смена", "Стоимость"]].values
        assigned_drivers = group["Водитель"].dropna().tolist()
        unassigned_shifts = group["Водитель"].isna().sum()
        num_drivers = len(assigned_drivers)
        num_shifts = len(shifts)
        large_number = 1e6
        cost_matrix = np.full((num_drivers, num_shifts), large_number)

        # Пропускаем случаи, где нет водителей или смен
        if num_drivers == 0 or num_shifts == 0:
            results.append(group)
            continue

        # Заполняем матрицу затрат
        for i, driver in enumerate(assigned_drivers):
            for j, (route_id, order_id, shift_id, shift_cost) in enumerate(shifts):
                if route_id in driver_routes.get(driver, []):
                    cost_matrix[i, j] = (
                        -shift_cost
                    )  # Инвертируем стоимость для максимизации

        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        # Сохраняем назначения и распределяем водителей на смены
        assignment = {}
        assigned_indices = set()
        for i, j in zip(row_ind, col_ind):
            if cost_matrix[i, j] > -large_number:
                assignment[(shifts[j][0], shifts[j][1], shifts[j][2])] = (
                    assigned_drivers[i]
                )
                assigned_indices.add(j)

        shift_costs = []
        assigned_count = 0

        # Добавляем водителей на смены, пока количество пропущенных смен не достигнет исходного значения
        for j, (route_id, order_id, shift_id, shift_cost) in enumerate(shifts):
            if j in assigned_indices and assigned_count < (
                num_shifts - unassigned_shifts
            ):
                assigned_driver = assignment.get((route_id, order_id, shift_id))
                shift_costs.append(
                    (
                        day,
                        department,
                        route_id,
                        order_id,
                        shift_id,
                        shift_cost,
                        assigned_driver,
                    )
                )
                assigned_count += 1
            else:
                # Проверяем, если причина в отсутствии водителя, который знает маршрут
                reason = "б/в"  # Изменяем на "б/в" вместо "No driver available"
                if all(cost_matrix[:, j] == large_number):
                    reason = "No qualified driver"
                shift_costs.append(
                    (day, department, route_id, order_id, shift_id, shift_cost, reason)
                )

        # Сохраняем результаты для текущей группы
        results.append(
            pd.DataFrame(
                shift_costs,
                columns=[
                    "day",
                    "dep",
                    "route_id",
                    "order_id",
                    "shift_id",
                    "shift_cost",
                    "assigned_driver",
                ],
            )
        )

    # Объединяем результаты в один DataFrame
    result_df = pd.concat(results, ignore_index=True)
    return result_df


def drivers_routes(df):
    """на основе прошлого месяца определяет, какие маршруты знает водитель"""
    df = df.dropna(subset=["Водитель"])
    dict_drivers_rt = (
        df.groupby("Водитель")["Маршрут"].apply(lambda x: list(set(x))).to_dict()
    )
    return dict_drivers_rt


def main() -> int:

    args = parse_args()
    month = months[args.month_number]
    coefficient_period = args.coef_period

    excel_df = pd.read_excel(
        os.environ[r"path_to_data"].replace("month", month),
        sheet_name="без 557 со сменами",
    )

    grouped_df = prepeare_df(excel_df, coefficient_period)

    # выясняем знание маршрутов водителями
    prev_month = months[(args.month_number - 2) % 12 + 1]
    prev_month_data = pd.read_excel(
        os.environ[r"path_to_data"].replace("month", prev_month),
        sheet_name="CSV без 557",
    )
    driver_route = drivers_routes(prev_month_data)

    today = pd.Timestamp.today().date()
    name = f"{today}_Shift_value_count_df_{month}).xlsx"
    grouped_df.to_excel(name, index=False)

    group_criterion = ["Маршрут", "Колонна", "Филиал"]
    for criterion in group_criterion:
        result = schedule_drivers(
            grouped_df, driver_route, criterion
        )  # по маршруту, колонне или филиалу
        result.to_excel(f"{today}-{criterion}--result-{month}.xlsx")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
