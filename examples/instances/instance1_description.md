# Input API Description

This document describes the structure and fields of the JSON file given as input to the scheduler.

## JSON Structure

The file consists of two main sections:
- `warehouse`: A list of materials stored in the warehouse, along with their stock levels and associated exchange points.
- `trucks`: A list of trucks that have to deliver or pick up materials.

### 1. Warehouse
The `warehouse` field is an array of objects representing materials stored in the warehouse. Each material has a unique identifier and is associated with one or more exchange points where it can be picked up or delivered. Each warehouse entry contains:

| Field           | Type    | Description |
|-----------------|---------|-------------|
| `material`      | String  | The unique identifier of the material.    |
| `stock_level`   | Integer | The current quantity of the material available in storage. |
| `stock_capacity` | Integer | The maximum capacity of the warehouse for this material.  |
| `exchange_points` | Array  | A list of exchange points (pickup and delivery locations) where the material can be transferred. |

#### Example:
```json
{
    "material": "M1",
    "stock_level": 20,
    "stock_capacity": 100,
    "exchange_points": ["P1", "P2"]
}
```

### 2. Trucks
The `trucks` field is an array of objects representing trucks that have to deliver or pick up materials. Each truck contains:

| Field          | Type    | Description |
|----------------|---------|-------------|
| `id`           | String  | The unique identifier of the truck. |
| `waiting_time` | Integer | The time (in minutes) the truck has been waiting in the yard. |
| `delivery_orders` | Array  | A list of delivery orders, where each order specifies a material, quantity, and the duration required for completion. |
| `pickup_orders`  | Array  | A list of pickup orders, where each order specifies a material, quantity, and the duration required for completion. |

Each `delivery_orders` and `pickup_orders` entry contains:

| Field      | Type    | Description |
|------------|---------|-------------|
| `material` | String  | The identifier of the material being delivered or picked up. |
| `quantity` | Integer | The amount of material being delivered or picked up. |
| `duration` | Integer | The duration in minutes for completing the order. |

#### Example:
```json
{
    "id": "T1",
    "waiting_time": 60,
    "delivery_orders": [
        {
            "material": "M1",
            "quantity": 10,
            "duration": 20
        }
    ],
    "pickup_orders": [
        {
            "material": "M2",
            "quantity": 20,
            "duration": 15
        }
    ]
}
```

