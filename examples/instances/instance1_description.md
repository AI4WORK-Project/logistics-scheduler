# Input API Description

This document describes the structure and fields of the JSON file given as input to the scheduler.

## JSON Structure

The file consists of three main sections:
- `warehouse`: A list of materials stored in the warehouse, along with their stock levels and associated exchange points.
- `trucks`: A list of trucks that have to deliver or pick up materials.
- `ongoing_orders`: A list of orders currently being processed at exchange points.

### 1. Warehouse
The `warehouse` field is an array of objects representing the exchange points. Each exchange point has a unique identifier and has associated one or more materials. Each warehouse entry contains:

| Field           | Type    | Description |
|-----------------|---------|-------------|
| `exchange_point` | String  | The unique identifier of the exchange point. |
| `materials`   | Array | A list of materials stored at the exchange point. |

Each `materials` entry contains:

| Field           | Type    | Description |
|-----------------|---------|-------------|
| `material`      | String  | The unique identifier of the material.    |
| `stock_level`   | Integer | The current quantity of the material available in storage. |
| `stock_capacity` | Integer | The maximum capacity for this material.  |

#### Example:
```json
{
    "exchange_point": "P1",
    "materials": [
        {
            "material": "M1",
            "stock_level": 20,
            "stock_capacity": 100
        },
        {
            "material": "M2",
            "stock_level": 50,
            "stock_capacity": 80
        }
    ]
}
```

### 2. Trucks
The `trucks` field is an array of objects representing trucks that have to deliver or pick up materials. Each truck contains:

| Field          | Type    | Description |
|----------------|---------|-------------|
| `id`           | String  | The unique identifier of the truck. |
| `waiting_time` | Integer | The time (in minutes) the truck has been waiting in the parking lot. |
| `order` | Object | The single order assigned to the truck. |

An `order` contains:

| Field      | Type    | Description |
|------------|---------|-------------|
| `is_delivery` | Boolean  | true = truck delivers material; false = truck picks up material. |
| `material` | String  | The identifier of the material being delivered or picked up. |
| `quantity` | Integer | The amount of material being delivered or picked up. |
| `duration` | Integer | The duration in minutes for completing the order. |
| `exchange_point` | Integer | The specific exchange point required for the order (optional). |

#### Example:
```json
{
    "id": "T1",
    "waiting_time": 60,
    "order": {
        "is_delivery": true,
        "material": "M1",
        "quantity": 10,
        "duration": 20,
        "exchange_point": "P1"
    }
}
```

### 3. Ongoing Orders
The `ongoing_orders` field is an array of objects representing the orders currently being processed at exchange points. Each entry contains:

| Field          | Type    | Description |
|----------------|---------|-------------|
| `exchange_point` | Integer | The exchange point where an order is in progress. |
| `remaining_duration` | Integer | The time (in minutes) left to finish the order. |

#### Example:
```json
{
    "exchange_point": "P1",
    "remaining_duration": 10
}
```

