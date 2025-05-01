from fastapi import APIRouter
from fastapi.responses import JSONResponse
from src.task_manager import TaskManager

router: APIRouter = APIRouter(prefix="/analytics")


@router.get("/agents/get")
async def get_agents() -> dict:
    return {
        "agents": {
            "agent1": {
                "status": "active",
                "tasks_completed": 5,
                "uptime": "2h 30m",
                "cpu_usage": 45.2,
                "memory_usage": "128MB",
                "last_task": "data processing",
                "efficiency_score": 0.89,
                "errors_encountered": 2,
            },
            "agent2": {
                "status": "idle",
                "tasks_completed": 3,
                "uptime": "1h 45m",
                "cpu_usage": 12.5,
                "memory_usage": "64MB",
                "last_task": "image recognition",
                "efficiency_score": 0.76,
                "errors_encountered": 1,
            },
            "agent3": {
                "status": "offline",
                "tasks_completed": 0,
                "uptime": "0h 0m",
                "cpu_usage": 0,
                "memory_usage": "0MB",
                "last_task": "N/A",
                "efficiency_score": 0,
                "errors_encountered": 0,
            },
            "agent4": {
                "status": "maintenance",
                "tasks_completed": 12,
                "uptime": "5h 15m",
                "cpu_usage": 5.7,
                "memory_usage": "256MB",
                "last_task": "system update",
                "efficiency_score": 0.95,
                "errors_encountered": 0,
            },
            "agent5": {
                "status": "overloaded",
                "tasks_completed": 8,
                "uptime": "3h 50m",
                "cpu_usage": 98.3,
                "memory_usage": "512MB",
                "last_task": "complex calculation",
                "efficiency_score": 0.62,
                "errors_encountered": 5,
            },
        }
    }


@router.get("/runs")
async def get_runs() -> dict:
    return {"runs": []}


@router.get("/history")
async def get_history() -> dict:
    return {"history": TaskManager.get_history()}


# Remote analytics
# Run count, waitlist users, etc


@router.get("/waitlist/data")
async def get_waitlist_data():
    pass


@router.get("/waitlist/count")
async def get_waitlist_count():
    pass


@router.get("/runs/count")
async def get_runs_count():
    pass


@router.get("/runs/data")
async def get_runs_data():
    pass


@router.get("/pricing")
async def get_pricing():
    return {
        "pricing": {
            "basic": {
                "monthly_cost": 50,
                "monthly_users": 500,
                "monthly_sessions": 5000,
            },
            "pro": {
                "monthly_cost": 100,
                "monthly_users": 1000,
                "monthly_sessions": 10000,
            },
            "enterprise": {
                "monthly_cost": 200,
                "monthly_users": 2000,
                "monthly_sessions": 20000,
            },
        }
    }


@router.get("/testimonials")
async def get_testimonials(min_stars: int = None, country: str = None):
    testimonials = [
        {
            "name": "John Smith",
            "stars": 5,
            "country": "USA",
            "date": "2024-03-15",
            "description": "Amazing product that has transformed our development workflow!",
        },
        {
            "name": "Marie Dubois",
            "stars": 4,
            "country": "France",
            "date": "2024-03-10",
            "description": "Very intuitive interface and great customer support.",
        },
        {
            "name": "Hans Mueller",
            "stars": 5,
            "country": "Germany",
            "date": "2024-03-08",
            "description": "The AI capabilities are incredible. Highly recommended!",
        },
        {
            "name": "Sofia Garcia",
            "stars": 4,
            "country": "Spain",
            "date": "2024-03-05",
            "description": "Has helped us ship features much faster.",
        },
        {
            "name": "James Wilson",
            "stars": 5,
            "country": "UK",
            "date": "2024-03-01",
            "description": "Best development tool we've used in years.",
        },
        {
            "name": "Yuki Tanaka",
            "stars": 5,
            "country": "Japan",
            "date": "2024-02-28",
            "description": "Excellent product with great attention to detail.",
        },
        {
            "name": "Lucas Silva",
            "stars": 4,
            "country": "Brazil",
            "date": "2024-02-25",
            "description": "Very powerful features that save us lots of time.",
        },
        {
            "name": "Anna Kowalski",
            "stars": 5,
            "country": "Poland",
            "date": "2024-02-20",
            "description": "The AI assistant is incredibly helpful.",
        },
        {
            "name": "Marco Rossi",
            "stars": 4,
            "country": "Italy",
            "date": "2024-02-15",
            "description": "Great tool for our development team.",
        },
        {
            "name": "Sarah Johnson",
            "stars": 5,
            "country": "Canada",
            "date": "2024-02-10",
            "description": "Has streamlined our entire development process.",
        },
        {
            "name": "Wei Chen",
            "stars": 4,
            "country": "China",
            "date": "2024-02-05",
            "description": "Very useful for our daily development tasks.",
        },
        {
            "name": "Emma Brown",
            "stars": 5,
            "country": "Australia",
            "date": "2024-02-01",
            "description": "Fantastic product that delivers on its promises.",
        },
        {
            "name": "Anders Nilsson",
            "stars": 4,
            "country": "Sweden",
            "date": "2024-01-28",
            "description": "Has made our coding much more efficient.",
        },
        {
            "name": "Maria Santos",
            "stars": 5,
            "country": "Portugal",
            "date": "2024-01-25",
            "description": "Outstanding tool for modern development.",
        },
        {
            "name": "David Kim",
            "stars": 4,
            "country": "South Korea",
            "date": "2024-01-20",
            "description": "Very impressed with the capabilities.",
        },
        {
            "name": "Elena Popov",
            "stars": 5,
            "country": "Russia",
            "date": "2024-01-15",
            "description": "Excellent support and feature set.",
        },
        {
            "name": "Mohammed Ahmed",
            "stars": 4,
            "country": "UAE",
            "date": "2024-01-10",
            "description": "Has greatly improved our productivity.",
        },
        {
            "name": "Priya Patel",
            "stars": 5,
            "country": "India",
            "date": "2024-01-05",
            "description": "The AI features are revolutionary.",
        },
        {
            "name": "Tom Anderson",
            "stars": 4,
            "country": "USA",
            "date": "2024-01-01",
            "description": "Very solid product with great features.",
        },
        {
            "name": "Nicole Martin",
            "stars": 5,
            "country": "France",
            "date": "2023-12-28",
            "description": "Best development tool we've used this year.",
        },
    ]

    filtered: list[dict] = testimonials

    if min_stars is not None:
        filtered = [t for t in filtered if t["stars"] >= min_stars]

    if country is not None:
        filtered = [t for t in filtered if t["country"].lower() == country.lower()]

    return JSONResponse({"testimonials": filtered})
