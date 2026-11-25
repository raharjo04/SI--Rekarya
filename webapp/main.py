from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from webapp.common import WEBAPP_DIR
from webapp.routes.audit import router as audit_router
from webapp.routes.dashboard import router as dashboard_router


app = FastAPI(
    title="SI-REKARYA",
    description="Dashboard analitik SDM berbasis persona karyawan.",
)
app.mount(
    "/static",
    StaticFiles(directory=str(WEBAPP_DIR / "static")),
    name="static",
)
app.include_router(dashboard_router)
app.include_router(audit_router)


@app.get("/health", include_in_schema=False)
def health_check() -> JSONResponse:
    return JSONResponse({"status": "ok"})
