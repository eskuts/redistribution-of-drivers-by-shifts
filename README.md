# Driver Shift Optimization: Linear Assignment Model

## Context

In logistics, assigning the right driver to the right shift isn't just about filling slots; it's about balancing costs and ensuring drivers actually know the routes they are assigned to. Manual scheduling often leads to sub-optimal cost distribution or "qualified driver" shortages.

I built this tool to automate shift distribution for a fleet. By applying mathematical modeling, I aimed to **maximize the total value of assigned shifts** while strictly respecting driver route knowledge. In testing, this approach ensures that 100% of assignments match drivers' historical route expertise while minimizing "empty" shifts.

---

## How it works

The core logic treats shift assignment as a classic **Assignment Problem**, solved using the Kuhn-Munkres (Hungarian) algorithm.

1. **Knowledge Mapping:** The script first analyzes the previous month's data to build a dictionary of which routes each driver is qualified for.
2. **Cost Matrix Construction:** For every day and department, I generate a cost matrix where:
* Rows represent available drivers.
* Columns represent open shifts.
* Values are the inverted shift costs (to convert a maximization problem into a minimization one).
* A "penalty" value () is applied if a driver does not know a specific route, effectively blocking that assignment.


3. **Optimization:** Using `scipy.optimize.linear_sum_assignment`, the engine finds the globally optimal pairing of drivers to shifts.
4. **Fallback Handling:** If a shift remains unassigned, the system tags it as "No qualified driver" or "b/v" (without driver), providing clear visibility into labor shortages versus routing conflicts.

---

## Tech Stack

* **Python 3.x**
* **Pandas & NumPy:** For data manipulation and matrix operations.
* **SciPy:** Specifically the `linear_sum_assignment` module for the optimization engine.
* **Openpyxl:** To handle Excel-based reporting and data input.

---

## Why it matters

This project moves the needle from "manual guesswork" to "data-driven allocation." It prevents the company from losing money on inefficient shift pairings and reduces the risk of operational delays caused by assigning drivers to unfamiliar routes. It’s a plug-and-play logic that can be scaled to any department (Column, Branch, or Route) by simply changing the grouping criterion.
