from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends # Import Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta, timezone
import pytz
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from models import UserInDB, TokenData # Import UserInDB
# from passlib.context import CryptContext # Import CryptContext
import json 
import os
import asyncio
import tempfile
import re
import subprocess
from pdf_generator import crear_pdf_recibo, generar_planilla
import daily_excel_logger # Import the new logger module

# webbrowser will be used only when running the app directly (not at import time)

# --- Load Product Configuration ---
try:
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    PRODUCTOS_COMPRA = config.get("productos_compra", [])
    PRODUCTOS_VENTA = config.get("productos_venta", [])
    print("Product configuration loaded successfully.")
except FileNotFoundError:
    print("Warning: config.json not found. Product dropdowns will be empty.")
    PRODUCTOS_COMPRA = []
    PRODUCTOS_VENTA = []
except json.JSONDecodeError:
    print("Warning: Could not decode config.json. Product dropdowns will be empty.")
    PRODUCTOS_COMPRA = []
    PRODUCTOS_VENTA = []


# --- Rate Limiting (Redis-backed with in-memory fallback) ---
from collections import defaultdict, deque
import asyncio
try:
    import redis.asyncio as redis_async
except Exception:
    redis_async = None

# In-memory fallback structures
_in_memory_counts: Dict[str, deque] = defaultdict(lambda: deque())
_rate_lock = asyncio.Lock()

# Rate limit configurable: env > config.json > default
DEFAULT_RATE_LIMIT = 300  # increased default
try:
    env_rl = os.getenv("APP_RATE_LIMIT_PER_MINUTE")
    if env_rl is not None and str(env_rl).strip() != "":
        RATE_LIMIT = max(1, int(float(env_rl)))
    else:
        RATE_LIMIT = int(config.get("rate_limit_per_minute", DEFAULT_RATE_LIMIT) or DEFAULT_RATE_LIMIT)
except Exception:
    RATE_LIMIT = DEFAULT_RATE_LIMIT

TIME_WINDOW = timedelta(minutes=1)


async def _get_redis_client():
    """Lazy initialize Redis client if available."""
    
    if not redis_async:
        return None
    # Create a client using default localhost:6379 - configurable if needed
    # Keep a module-level client to reuse connections
    if not hasattr(_get_redis_client, "client") or _get_redis_client.client is None:
        try:
            _get_redis_client.client = redis_async.Redis()
            # Optional: test connection (short timeout)
            await _get_redis_client.client.ping()
        except Exception:
            # If Redis is unreachable, fall back to in-memory
            _get_redis_client.client = None
    return _get_redis_client.client


class RateLimitingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Prefer X-Forwarded-For when behind proxies
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        # Try Redis first (distributed, efficient)
        redis_client = await _get_redis_client()
        if redis_client:
            try:
                key = f"rate:{client_ip}"
                # INCR is atomic; set expiry when key appears
                count = await redis_client.incr(key)
                if count == 1:
                    await redis_client.expire(key, int(TIME_WINDOW.total_seconds()))
                if count > RATE_LIMIT:
                    return Response(content="Too Many Requests", status_code=429)
            except Exception:
                # On any Redis error, fall back to in-memory below
                redis_client = None

        if not redis_client:
            # In-memory fallback with per-process locking
            now = datetime.now(timezone.utc)
            async with _rate_lock:
                dq = _in_memory_counts[client_ip]
                # Drop old timestamps
                while dq and now - dq[0] >= TIME_WINDOW:
                    dq.popleft()
                if len(dq) >= RATE_LIMIT:
                    return Response(content="Too Many Requests", status_code=429)
                dq.append(now)

        response = await call_next(request)
        return response

# --- Base Model ---
class BasePesada(BaseModel):
    id: Optional[int] = None
    mercaderia: Optional[str] = Field(default="", description="Type of merchandise")
    bruto: Optional[float] = Field(default=None, ge=0, description="Gross weight in kilograms")
    tara: Optional[float] = Field(default=None, ge=0, description="Tare weight in kilograms") # Must be greater than or equal to 0
    merma: Optional[float] = Field(default=None, ge=0, description="Shrinkage in kilograms") # Must be greater than or equal to 0
    neto: Optional[float] = Field(default=None, description="Net weight in kilograms (calculated)")
    precio_kg: Optional[float] = Field(default=None, ge=0, description="Price per kilogram")
    importe: Optional[float] = Field(default=None, description="Total amount (calculated)")
    fecha: Optional[str] = Field(default=None, description="Date of operation (dd/mm/yy)")
    hora_ingreso: Optional[str] = Field(default=None, description="Time of entry (HH:MM)")
    hora_salida: Optional[str] = Field(default=None, description="Time of exit (HH:MM)")
    observaciones: Optional[str] = Field(default=None, description="Additional observations")


# --- Compra Model ---
class Compra(BasePesada):
    proveedor: str = Field(..., min_length=1, description="Supplier name")
    chofer: Optional[str] = Field(default=None, description="Driver name")
    patente: Optional[str] = Field(default=None, description="Vehicle license plate")

# --- Modelo para actualización de Compra ---
class CompraUpdate(BasePesada):
    proveedor: Optional[str] = None
    chofer: Optional[str] = None
    patente: Optional[str] = None

# --- Venta Model ---
class Venta(BasePesada):
    cliente: str = Field(..., min_length=1, description="Client name")
    transporte: Optional[str] = Field(default=None, description="Transport company name")
    patente: Optional[str] = Field(default=None, description="Vehicle license plate")
    incoterm: Optional[str] = Field(default=None, description="Incoterm for the sale (CIF/FOB)")
    remito: Optional[int] = Field(default=None, description="Número de remito (solo números)")

# --- Modelo para actualización de Venta ---
class VentaUpdate(BasePesada):
    cliente: Optional[str] = None
    transporte: Optional[str] = None
    patente: Optional[str] = None
    incoterm: Optional[str] = None
    remito: Optional[int] = None

app = FastAPI()

# --- CORS Configuration ---
# This should be one of the first middleware added
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for VPS deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Headers are now defined within daily_excel_logger.py
# No need to set them here anymore.

# Add the middleware to the app
app.add_middleware(RateLimitingMiddleware)

# --- In-memory Storage (DEPRECATED - Data will be read from Excel on demand) ---
# compra_counter = 0 
# venta_counter = 0
# compras_entries: Dict[int, Dict[str, Any]] = {} 
# ventas_entries: Dict[int, Dict[str, Any]] = {} 
connected_clients: List[WebSocket] = []

# --- Password Hashing ---
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- In-memory User Storage (for demonstration) ---
# In a real application, this would be a database
users_db: Dict[str, UserInDB] = {}

# Load users from users.json (Plain text passwords for now)
try:
    with open("users.json", "r", encoding="utf-8") as f:
        users_data = json.load(f)
        for username, data in users_data.items():
            # Store plain text password in hashed_password field for compatibility
            users_db[username] = UserInDB(
                username=username, 
                hashed_password=data["password"], 
                role=data["role"], 
                password=""
            )
    print(f"Loaded {len(users_db)} users from users.json")
except FileNotFoundError:
    print("Warning: users.json not found. No users loaded.")
except Exception as e:
    print(f"Error loading users.json: {e}")

# Add default users (replace with secure registration in production)
# Eliminar el hasheo inicial de contraseñas para evitar errores en el entorno de despliegue
#hashed_password_admin = pwd_context.hash("ronan1")
#users_db["admin"] = UserInDB(username="admin", hashed_password=hashed_password_admin, role="admin", password="")

# hashed_password_lect = pwd_context.hash("ronan2")
# users_db["admin2"] = UserInDB(username="admin2", hashed_password=hashed_password_lect, role="lect", password="") # password field is not stored
 
# Añadido: usuario adicional admin3 (contraseña: ronan3)
# hashed_password_admin3 = pwd_context.hash("ronan3")
# users_db["admin3"] = UserInDB(username="admin3", hashed_password=hashed_password_admin3, role="lect", password="") # password field is not stored

# Añadido: usuario adicional admin4 (contraseña: ronan4)
# hashed_password_admin4 = pwd_context.hash("ronan4")
# users_db["admin4"] = UserInDB(username="admin4", hashed_password=hashed_password_admin4, role="lect", password="") # password field is not stored

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm # Import OAuth2PasswordBearer and OAuth2PasswordRequestForm
from jose import JWTError, jwt # Import JWTError and jwt
from datetime import timedelta # Import timedelta

def get_user(username: str) -> Optional[UserInDB]:
    """Retrieve a user from the in-memory database."""
    return users_db.get(username)

# --- Authentication ---
SECRET_KEY = "your-secret-key" # Change this in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 540 # Token expires in 9 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # Define OAuth2 scheme

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15) # Default expiration
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user(form_data.username)
    # Plain text password verification
    if not user or form_data.password != user.hashed_password:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "roles": [user.role]}, # Include roles in token
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Authorization Dependencies ---
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        roles: List[str] = payload.get("roles", []) # Get roles from token
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, roles=roles)
    except JWTError:
        raise credentials_exception
    user = get_user(username)
    if user is None:
        raise credentials_exception
    return user

def has_role(required_roles: List[str]):
    def role_checker(current_user: UserInDB = Depends(get_current_user)):
        # Check if the user's role is in the list of required roles
        if current_user.role not in required_roles:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return current_user
    return role_checker


# --- Load data from Excel on startup (DEPRECATED) ---
# No longer loading all data into memory on startup.
# Data will be read from the specific sheet on each request.
compras_entries: Dict[int, Dict[str, Any]] = {} # Keep for now for write operations
ventas_entries: Dict[int, Dict[str, Any]] = {} # Keep for now for write operations
compra_counter = 0
venta_counter = 0
try:
    # We can still load today's data for write operations to work temporarily
    daily_data = daily_excel_logger.load_daily_data()
    compras_entries = {entry["id"]: entry for entry in daily_data.get("Compra", []) if entry.get("id") is not None}
    ventas_entries = {entry["id"]: entry for entry in daily_data.get("Venta", []) if entry.get("id") is not None}
    compra_counter = max(compras_entries.keys()) if compras_entries else 0
    venta_counter = max(ventas_entries.keys()) if ventas_entries else 0
    print(f"Loaded today's data for write operations: {len(compras_entries)} compras, {len(ventas_entries)} ventas.")
except Exception as e:
    print(f"Could not preload today's data for write operations: {e}")


# --- Helper Functions ---
def calculate_neto(bruto: Optional[float], tara: Optional[float], merma: Optional[float]) -> Optional[float]:
    """Calculates neto if bruto and tara are present. Maneja errores de tipo y valor."""
    try:
        if bruto is not None and tara is not None:
            return float(bruto) - float(tara) - (float(merma) if merma is not None else 0)
        return None
    except (TypeError, ValueError) as e:
        print(f"Error calculando neto: {e}")
        return None

def calculate_importe(neto: Optional[float], precio_kg: Optional[float]) -> Optional[float]:
    """Calculates importe if neto and precio_kg are present. Maneja errores de tipo y valor."""
    try:
        if neto is not None and precio_kg is not None:
            return float(neto) * float(precio_kg)
        return None
    except (TypeError, ValueError) as e:
        print(f"Error calculando importe: {e}")
        return None

def get_current_time() -> str:
    """Returns current time in HH:MM format. Maneja errores de obtención de hora."""
    try:
        tz = pytz.timezone('America/Argentina/Buenos_Aires')
        return datetime.now(tz).strftime("%H:%M")
    except Exception as e:
        print(f"Error obteniendo hora actual: {e}")
        return "00:00"

def get_current_date() -> str:
    """Returns current date in dd/mm/yy format. Maneja errores de obtención de fecha."""
    try:
        tz = pytz.timezone('America/Argentina/Buenos_Aires')
        return datetime.now(tz).strftime("%d/%m/%y")
    except Exception as e:
        print(f"Error obteniendo fecha actual: {e}")
        return "01/01/70"

def get_daily_pesadas_folder() -> str:
    """Returns the path for today's pesadas folder, creating it if necessary. Maneja errores de acceso a disco."""
    try:
        today_str = datetime.now().strftime("%d-%m-%Y")
        folder_path = os.path.join("pesadas", today_str)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        return folder_path
    except Exception as e:
        print(f"Error creando/accediendo a carpeta de pesadas: {e}")
        return "pesadas/error"


def get_pesadas_folder_for_date(date_str: str) -> str:
    """Returns (and creates) the pesadas folder for a given date string in YYYY-MM-DD format.
    The folder name uses dd-mm-YYYY to keep compatibility with existing folders.
    """
    try:
        # Convert YYYY-MM-DD to dd-mm-YYYY
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        folder_name = dt.strftime("%d-%m-%Y")
        folder_path = os.path.join("pesadas", folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        return folder_path
    except Exception as e:
        print(f"Error creando/accediendo a carpeta de pesadas para fecha {date_str}: {e}")
        # Fallback to today's folder
        return get_daily_pesadas_folder()


def get_planilla_folder_for_date(date_str: str) -> str:
    """Returns (and creates) the Planilla folder for a given date string in YYYY-MM-DD format.
    Folder name uses dd-mm-YYYY.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        folder_name = dt.strftime("%d-%m-%Y")
        folder_path = os.path.join("Planilla", folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        return folder_path
    except Exception as e:
        print(f"Error creando/accediendo a carpeta Planilla para fecha {date_str}: {e}")
        # Fallback to today's planilla folder
        return get_planilla_folder_for_today()


def get_planilla_folder_for_today() -> str:
    """Returns the path for today's Planilla folder, creating it if necessary."""
    try:
        today_str = datetime.now().strftime("%d-%m-%Y")
        folder_path = os.path.join("Planilla", today_str)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        return folder_path
    except Exception as e:
        print(f"Error creando/accediendo a carpeta de planilla: {e}")
        return os.path.join("Planilla", "error")


def get_daily_backup_folder_for_today() -> str:
    """Returns the path for today's Daily_BackUp folder, creating it if necessary."""
    try:
        today_str = datetime.now().strftime("%d-%m-%Y")
        folder_path = os.path.join("Daily_BackUp", today_str)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        return folder_path
    except Exception as e:
        print(f"Error creando/accediendo a carpeta de backup diario: {e}")
        return os.path.join("Daily_BackUp", "error")


def _ensure_sumatrapdf():
    """Ensure SumatraPDF is available, download if necessary."""
    sumatra_dir = os.path.join(os.getcwd(), "SumatraPDF")
    sumatra_exe = os.path.join(sumatra_dir, "SumatraPDF.exe")
    
    # Check if already exists
    if os.path.exists(sumatra_exe):
        return sumatra_exe
    
    # Check if download was already attempted
    download_marker = os.path.join(sumatra_dir, ".download_attempted")
    if os.path.exists(download_marker):
        return None  # Don't keep trying to download
    
    try:
        import urllib.request
        import zipfile
        
        print("Descargando SumatraPDF...")
        
        # Create directory if it doesn't exist
        os.makedirs(sumatra_dir, exist_ok=True)
        
        # Download SumatraPDF portable version
        url = "https://www.sumatrapdfreader.org/dl/rel/3.5.2/SumatraPDF-3.5.2-64.zip"
        zip_path = os.path.join(sumatra_dir, "sumatra.zip")
        
        urllib.request.urlretrieve(url, zip_path)
        
        # Extract the exe
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Find SumatraPDF executable (could have different names)
            for file_info in zip_ref.infolist():
                if ('SumatraPDF' in file_info.filename and 
                    file_info.filename.endswith('.exe')):
                    # Extract to target directory
                    extracted_path = zip_ref.extract(file_info, sumatra_dir)
                    # Rename to standard name if needed
                    if extracted_path != sumatra_exe:
                        if os.path.exists(sumatra_exe):
                            os.remove(sumatra_exe)
                        os.rename(extracted_path, sumatra_exe)
                    break
        
        # Clean up zip file
        os.remove(zip_path)
        
        if os.path.exists(sumatra_exe):
            print("SumatraPDF descargado exitosamente")
            return sumatra_exe
        else:
            # Mark that we tried to download
            with open(download_marker, 'w') as f:
                f.write("download attempted")
            return None
            
    except Exception as e:
        print(f"Error descargando SumatraPDF: {e}")
        # Mark that we tried to download
        try:
            os.makedirs(sumatra_dir, exist_ok=True)
            with open(download_marker, 'w') as f:
                f.write("download attempted")
        except:
            pass
        return None


import platform

def _try_print_file_windows(filepath: str, copies: int = 1):
    """Try to print a file using the system's default printer.
    Supports Windows (SumatraPDF/win32api) and Linux (lp).
    """
    system_name = platform.system()
    print(f"DEBUG: Sistema detectado para impresión: {system_name}")

    if system_name == "Linux":
        # On Linux remote servers, we don't try to print directly
        # The PDF will be returned to the browser for client-side printing
        print(f"✓ PDF preparado para descarga/visualización en Linux ({copies} copias solicitadas): {filepath}")
        return

    elif system_name == "Windows":
        # Windows logic
        
        # First, ensure SumatraPDF is available
        sumatra_exe = _ensure_sumatrapdf()
        
        # Try using SumatraPDF in silent mode (background printing)
        sumatra_paths = [
            sumatra_exe,  # From download
            os.path.join("SumatraPDF", "SumatraPDF.exe"),
            os.path.join(os.getcwd(), "SumatraPDF", "SumatraPDF.exe"),
            "SumatraPDF.exe",  # If it's in PATH
            r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
            r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe"
        ]
        
        for sumatra_path in sumatra_paths:
            if sumatra_path and os.path.exists(sumatra_path):
                try:
                    # Use SumatraPDF with -silent flag for background printing
                    # -print-settings "Nx" prints N copies
                    subprocess.run([
                        sumatra_path,
                        "-silent",
                        "-print-to-default",
                        "-print-settings", f"{copies}x",
                        str(filepath)
                    ], check=True, timeout=30)
                    print(f"✓ Impreso usando SumatraPDF en modo silencioso ({copies} copias): {filepath}")
                    return
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                    print(f"Error con SumatraPDF en {sumatra_path}: {e}")
                    continue
                except Exception as e:
                    print(f"Error inesperado con SumatraPDF en {sumatra_path}: {e}")
                    continue
        
        # Fallback to win32api if SumatraPDF is not available
        try:
            # Import at runtime to avoid import-time failures on non-Windows runners
            import win32api  # type: ignore
            print(f"SumatraPDF no disponible, usando impresión por defecto de Windows: {filepath}")
            # win32api.ShellExecute does not easily support copies, so we loop
            for _ in range(copies):
                win32api.ShellExecute(0, "print", str(filepath), None, ".", 0)
                # Small delay between print jobs to avoid overwhelming the spooler
                if copies > 1:
                    import time
                    time.sleep(1)
        except Exception as e:
            # Wrap and raise a generic exception so callers can produce an HTTP response
            raise Exception(f"Error de impresión: No se pudo imprimir ni con SumatraPDF ni con el sistema por defecto: {e}")

    else:
        raise Exception(f"Impresión no soportada en este sistema operativo: {system_name}")


# --- Sanitization & Validation helpers ---
CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")

def sanitize_str(value: Optional[str], max_len: int = 250) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    # remove control chars, keep printable including accents
    s = CONTROL_CHARS_RE.sub('', value)
    s = s.strip()
    if len(s) > max_len:
        s = s[:max_len]
    return s

def validate_numeric(value, name: str, min_value: float = 0.0, max_value: float = 1e7):
    if value is None or value == "":
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"Campo '{name}' debe ser numérico.")
    if num < min_value or num > max_value:
        raise HTTPException(status_code=400, detail=f"Campo '{name}' fuera de rango ({min_value} - {max_value}).")
    return num


def _format_save_error(e: Exception) -> str:
    """Format Excel save errors to return clearer HTTP messages."""
    try:
        if isinstance(e, PermissionError) or "Permission denied" in str(e):
            return f"Error al guardar en Excel: permiso denegado. Asegúrese de que 'daily_log.xlsx' no esté abierto en Excel u otro proceso. ({e})"
    except Exception:
        pass
    return f"Error al guardar en Excel: {e}"

# --- WebSocket Logic ---
async def notify_clients(data_type: str):
    """Send updates of a specific type to all connected clients."""
    if connected_clients:
        if data_type == "compra":
            data = list(compras_entries.values())
        elif data_type == "venta":
            data = list(ventas_entries.values())
        else:
            return # Unknown type

        message = {"type": data_type, "payload": data}
        # Use gather for concurrent sending
        results = await asyncio.gather(
            *[client.send_json(message) for client in connected_clients],
            return_exceptions=True # Prevent one failed send from stopping others
        )
        # Optional: Log or handle exceptions from results if needed
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Error sending to client {i}: {result}")
                try:
                    connected_clients[i].close()
                except Exception as e:
                    print(f"Error cerrando conexión con cliente {i}: {e}")
                finally:
                    connected_clients.pop(i)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    print(f"Client connected. Total clients: {len(connected_clients)}")
    try:
        # Send initial data for both types
        initial_compras = {"type": "compra", "payload": list(compras_entries.values())}
        initial_ventas = {"type": "venta", "payload": list(ventas_entries.values())}
        await websocket.send_json(initial_compras)
        await websocket.send_json(initial_ventas)

        while True:
            # Keep connection alive, listening for messages (though none are expected from client currently)
            await websocket.receive_text()
    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        print(f"Client removed. Total clients: {len(connected_clients)}")


# --- System Configuration Endpoint ---
@app.get("/api/system/config")
async def get_system_config():
    """Returns system configuration including OS type for frontend routing."""
    import platform
    os_type = platform.system().lower()  # 'windows', 'linux', 'darwin'
    return {
        "os_type": os_type,
        "server_type": "local" if os_type == "windows" else "remote"
    }

# --- Product Catalog Endpoints ---
@app.get("/api/productos/compras", response_model=List[str])
async def get_productos_compras(current_user: UserInDB = Depends(has_role(["admin", "lect"]))):
    """Returns the list of products available for purchase."""
    return PRODUCTOS_COMPRA

@app.get("/api/productos/ventas", response_model=List[str])
async def get_productos_ventas(current_user: UserInDB = Depends(has_role(["admin", "lect"]))):
    """Returns the list of products available for sale."""
    return PRODUCTOS_VENTA


# --- Compras Endpoints ---
@app.get("/filter_section_dato")
async def filter_section_dato(section: str, search: str = "", start_date: str = None, end_date: str = None, current_user: UserInDB = Depends(has_role(["admin", "lect"]))):
    """
    Filtra compras o ventas por rango de fechas (YYYY-MM-DD) y término de búsqueda.
    """
    import daily_excel_logger
    from datetime import datetime
    # Validar sección
    if section not in ["compras", "ventas"]:
        return JSONResponse(content={"error": "Sección inválida"}, status_code=400)
    tipo = "Compra" if section == "compras" else "Venta"
    # Validar fechas
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
    except Exception:
        return JSONResponse(content={"error": "Formato de fecha inválido"}, status_code=400)
    resultados = []
    # Recorrer días en rango
    if start_dt and end_dt:
        delta = (end_dt - start_dt).days
        for i in range(delta + 1):
            fecha_actual = (start_dt + timedelta(days=i)).strftime("%Y-%m-%d")
            datos = daily_excel_logger.load_data_by_date(fecha_actual)
            items = datos.get(tipo, [])
            if search:
                items = [e for e in items if search.lower() in json.dumps(e, ensure_ascii=False).lower()]
            resultados.extend(items)
    else:
        # Si no hay rango, usar hoy
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        datos = daily_excel_logger.load_data_by_date(fecha_actual)
        items = datos.get(tipo, [])
        if search:
            items = [e for e in items if search.lower() in json.dumps(e, ensure_ascii=False).lower()]
        resultados.extend(items)
    return JSONResponse(content=resultados)
@app.get("/compras", response_model=List[Compra])
async def read_compras_entries(
    search: Optional[str] = None,
    date: Optional[str] = None,
    current_user: UserInDB = Depends(has_role(["admin", "lect"]))
):
    """
    Retrieve compra entries from a specific date sheet in Excel,
    with optional filtering.
    """
    # If no date is provided, default to today's date in YYYY-MM-DD format
    target_date_str = date if date else datetime.now().strftime("%Y-%m-%d")

    # Load data from the specific sheet
    all_data_for_date = daily_excel_logger.load_data_by_date(target_date_str)
    filtered_entries = all_data_for_date.get("Compra", [])

    # Filter by search term on the loaded data
    if search:
        search_term = search.lower()
        filtered_entries = [
            entry for entry in filtered_entries
            if search_term in str(entry.get("proveedor", "")).lower() or \
               search_term in str(entry.get("mercaderia", "")).lower() or \
               search_term in str(entry.get("chofer", "")).lower() or \
               search_term in str(entry.get("patente", "")).lower()
        ]
        
    return filtered_entries

@app.post("/compras", response_model=Compra)
async def create_compra_entry(compra_data: Compra, current_user: UserInDB = Depends(has_role(["admin"]))):
    """Create a new compra entry. This will always be for the CURRENT day."""
    global compra_counter, compras_entries

    # --- Recalculate counter based on current day's sheet to avoid ID conflicts ---
    try:
        todays_data = daily_excel_logger.load_daily_data()
        todays_compras = {entry["id"]: entry for entry in todays_data.get("Compra", []) if entry.get("id") is not None}
        compra_counter = max(todays_compras.keys()) if todays_compras else 0
    except Exception as e:
        print(f"Could not recalculate compra_counter, defaulting to in-memory. Error: {e}")
    # --- End recalculation ---

    compra_counter += 1
    new_id = compra_counter # Use simple integer ID
    compra_data.id = new_id
    compra_data.fecha = get_current_date()
    current_time = get_current_time()

    # Validate numeric fields first to avoid setting timestamps when empty strings are provided
    compra_data.bruto = validate_numeric(compra_data.bruto, 'bruto')
    compra_data.tara = validate_numeric(compra_data.tara, 'tara')
    compra_data.merma = validate_numeric(compra_data.merma, 'merma')
    compra_data.precio_kg = validate_numeric(compra_data.precio_kg, 'precio_kg')

    # Set times only when validated numeric values are present
    if compra_data.bruto is not None:
        compra_data.hora_ingreso = current_time
    if compra_data.tara is not None:
        compra_data.hora_salida = current_time

    compra_data.neto = calculate_neto(compra_data.bruto, compra_data.tara, compra_data.merma)
    compra_data.importe = calculate_importe(compra_data.neto, compra_data.precio_kg)

    # Sanitize string fields and ensure mercaderia is stored correctly
    entry_dict = compra_data.dict()
    entry_dict["mercaderia"] = sanitize_str(entry_dict.get("mercaderia"))
    entry_dict["proveedor"] = sanitize_str(entry_dict.get("proveedor"))
    entry_dict["chofer"] = sanitize_str(entry_dict.get("chofer"))
    entry_dict["patente"] = sanitize_str(entry_dict.get("patente"), max_len=20)
    entry_dict["observaciones"] = sanitize_str(entry_dict.get("observaciones"), max_len=1000)

    # Use the integer ID as the key for the dictionary
    compras_entries[new_id] = entry_dict 
    
    # --- Upsert to Excel ---
    try:
        # Prepare data row according to new daily_excel_logger.HEADERS
        data_row = [
            entry_dict.get("id"), # Registro ID
            "Compra", # Tipo Operación
            entry_dict.get("proveedor", ""), # Contraparte
            entry_dict.get("mercaderia", ""), # Producto
            entry_dict.get("bruto"), # Peso Bruto (kg)
            entry_dict.get("tara"), # Peso Tara (kg)
            entry_dict.get("merma"), # Merma (kg)
            entry_dict.get("neto"), # Peso Neto (kg)
            entry_dict.get("precio_kg"), # Precio x Kg
            entry_dict.get("importe"), # Importe
            entry_dict.get("chofer", ""), # Chofer
            entry_dict.get("patente", ""), # Patente
            "", # Incoterm (solo aplica a Ventas)
            entry_dict.get("fecha", ""), # Fecha Operación
            entry_dict.get("hora_ingreso", ""), # Hora Ingreso
            entry_dict.get("hora_salida", ""), # Hora Salida
            "", # Remito (no aplica a Compras)
            entry_dict.get("observaciones", "") # Observaciones - Added
        ]
        # Convert None to empty string for Excel compatibility
        data_row_cleaned = ["" if v is None else v for v in data_row]
        # Use the integer ID and type for upserting
        daily_excel_logger.upsert_data(entry_id=new_id, entry_type="Compra", data_row=data_row_cleaned)
        # Verify write by reloading today's data and checking the ID exists
        reloaded = daily_excel_logger.load_daily_data()
        todays_compras = {entry["id"]: entry for entry in reloaded.get("Compra", []) if entry.get("id") is not None}
        if new_id not in todays_compras:
            logger_msg = f"Post-upsert verification failed: Compra {new_id} not found in today's sheet."
            print(logger_msg)
            raise HTTPException(status_code=500, detail=logger_msg)
    except Exception as e:
        # Log the error and raise an HTTPException with clearer message
        print(f"Error upserting Compra {new_id} to Excel: {e}")
        raise HTTPException(status_code=500, detail=_format_save_error(e))

    await notify_clients("compra")
    # Return using the integer ID
    return compras_entries[new_id]

# Revert path parameter and type hint to int

@app.put("/compras/{compra_id}", response_model=Compra)
async def update_compra_entry(compra_id: int, compra_data: CompraUpdate, current_user: UserInDB = Depends(has_role(["admin"]))):
    """Update an existing compra entry."""
    if compra_id not in compras_entries:
        # Fallback: intentar cargar la compra del día actual desde Excel
        try:
            todays = daily_excel_logger.load_daily_data().get("Compra", [])
            found = next((e for e in todays if int(e.get("id") or -1) == int(compra_id)), None)
            if found:
                compras_entries[compra_id] = found
            else:
                raise HTTPException(status_code=404, detail="Compra no encontrada (puede ser de otra fecha)")
        except HTTPException:
            raise
        except Exception as e:
            print(f"Fallback load for Compra {compra_id} failed: {e}")
            raise HTTPException(status_code=404, detail="Compra no encontrada")

    current_entry = compras_entries[compra_id]
    update_data = compra_data.dict(exclude_unset=True)

    # Preserve existing timestamps unless new valid weights are added
    if "bruto" in update_data:
        # Validate incoming bruto (will raise HTTPException if invalid)
        validated_bruto = validate_numeric(update_data.get("bruto"), 'bruto')
        update_data["bruto"] = validated_bruto
        if validated_bruto is not None and current_entry.get("hora_ingreso") is None:
            update_data["hora_ingreso"] = get_current_time()
        else:
            update_data["hora_ingreso"] = current_entry.get("hora_ingreso")
    else:
        update_data["hora_ingreso"] = current_entry.get("hora_ingreso")

    if "tara" in update_data:
        validated_tara = validate_numeric(update_data.get("tara"), 'tara')
        update_data["tara"] = validated_tara
        if validated_tara is not None and current_entry.get("hora_salida") is None:
            update_data["hora_salida"] = get_current_time()
        else:
            update_data["hora_salida"] = current_entry.get("hora_salida")
    else:
        update_data["hora_salida"] = current_entry.get("hora_salida")

    # Validate other numeric fields in the update payload if present
    if "merma" in update_data:
        update_data["merma"] = validate_numeric(update_data.get("merma"), 'merma')
    if "precio_kg" in update_data:
        update_data["precio_kg"] = validate_numeric(update_data.get("precio_kg"), 'precio_kg')

    update_data["fecha"] = current_entry.get("fecha")
    update_data["id"] = compra_id

    merged_data = {**current_entry, **update_data}
    merged_data["neto"] = calculate_neto(merged_data.get("bruto"), merged_data.get("tara"), merged_data.get("merma"))
    merged_data["importe"] = calculate_importe(merged_data.get("neto"), merged_data.get("precio_kg"))

    if "mercaderia" in merged_data and merged_data["mercaderia"] is None:
        merged_data["mercaderia"] = ""

    compras_entries[compra_id] = merged_data

    try:
        data_row = [
            merged_data.get("id"),
            "Compra",
            merged_data.get("proveedor", ""),
            merged_data.get("mercaderia", ""),
            merged_data.get("bruto"),
            merged_data.get("tara"),
            merged_data.get("merma"),
            merged_data.get("neto"),
            merged_data.get("precio_kg"),
            merged_data.get("importe"),
            merged_data.get("chofer", ""),
            merged_data.get("patente", ""),
            "", # Incoterm (solo aplica a Ventas)
            merged_data.get("fecha", ""),
            merged_data.get("hora_ingreso", ""),
            merged_data.get("hora_salida", ""),
            "", # Remito (no aplica a Compras)
            merged_data.get("observaciones", "")
        ]
        data_row_cleaned = ["" if v is None else v for v in data_row]
        daily_excel_logger.upsert_data(entry_id=compra_id, entry_type="Compra", data_row=data_row_cleaned)
    except Exception as e:
        print(f"Error upserting Compra {compra_id} to Excel: {e}")
        raise HTTPException(status_code=500, detail=_format_save_error(e))

    # Verify write by reloading today's data and checking the ID exists (post-update read-back)
    try:
        reloaded = daily_excel_logger.load_daily_data()
        todays_compras = {entry["id"]: entry for entry in reloaded.get("Compra", []) if entry.get("id") is not None}
        if compra_id not in todays_compras:
            logger_msg = f"Post-update verification failed: Compra {compra_id} not found in today's sheet."
            print(logger_msg)
            raise HTTPException(status_code=500, detail=logger_msg)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error verifying updated Compra {compra_id}: {e}")
        raise HTTPException(status_code=500, detail=_format_save_error(e))

    await notify_clients("compra")
    return compras_entries[compra_id]

# Revert path parameter and type hint to int
@app.delete("/compras/{compra_id}")
async def delete_compra_entry(compra_id: int, current_user: UserInDB = Depends(has_role(["admin"]))):
    """Delete a compra entry."""
    # Use integer ID for lookup
    if compra_id not in compras_entries:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    try:
        # Use integer ID and type for deletion
        daily_excel_logger.delete_data(entry_id=compra_id, entry_type="Compra")
    except Exception as e:
        # Log the error and raise an HTTPException
        print(f"Error deleting Compra {compra_id} from Excel: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting compra entry from Excel: {e}")

    # Use integer ID to delete from memory
    del compras_entries[compra_id]
    await notify_clients("compra")
    return {"message": "Compra eliminada correctamente"}

# Revert path parameter and type hint to int
@app.get("/compras/{compra_id}/imprimir")
async def imprimir_compra_pdf(compra_id: int, copies: int = 2, date: Optional[str] = None, current_user: UserInDB = Depends(has_role(["admin", "lect"]))):
    """Generate and return PDF for a specific compra entry (Client-side printing)."""
    
    # First try in-memory (today's data)
    datos = None
    should_upsert = True

    if compra_id in compras_entries:
        datos = [compras_entries[compra_id]]
    else:
        # If a date was provided, try to load the entry from that date's sheet
        if date:
            try:
                entries = daily_excel_logger.load_data_by_date(date)
                compras_for_date = entries.get("Compra", [])
                found = next((e for e in compras_for_date if int(e.get("id")) == int(compra_id)), None)
                if found:
                    datos = [found]
                    should_upsert = False  # Do not upsert when printing historical record
                else:
                    raise HTTPException(status_code=404, detail="Compra no encontrada en la fecha solicitada")
            except HTTPException:
                raise
            except Exception as e:
                print(f"Error cargando Compra {compra_id} para la fecha {date}: {e}")
                raise HTTPException(status_code=500, detail=f"Error cargando datos: {e}")
        else:
            raise HTTPException(status_code=404, detail="Compra no encontrada")

    # If this is today's record and we have it in memory, ensure it's saved before printing
    if should_upsert and datos and compra_id in compras_entries:
        try:
            entry_dict = compras_entries[compra_id]
            data_row = [
                entry_dict.get("id"),
                "Compra",
                entry_dict.get("proveedor", ""),
                entry_dict.get("mercaderia", ""),
                entry_dict.get("bruto"),
                entry_dict.get("tara"),
                entry_dict.get("merma"),
                entry_dict.get("neto"),
                entry_dict.get("precio_kg"),
                entry_dict.get("importe"),
                entry_dict.get("chofer", ""),
                entry_dict.get("patente", ""),
                "", # Incoterm (solo aplica a Ventas)
                entry_dict.get("fecha", ""),
                entry_dict.get("hora_ingreso", ""),
                entry_dict.get("hora_salida", ""),
                "", # Remito (no aplica a Compras)
                entry_dict.get("observaciones", "")
            ]
            data_row_cleaned = ["" if v is None else v for v in data_row]
            daily_excel_logger.upsert_data(entry_id=compra_id, entry_type="Compra", data_row=data_row_cleaned)
        except Exception as e:
            print(f"Error saving Compra {compra_id} before printing: {e}")
            raise HTTPException(status_code=500, detail=_format_save_error(e))

    try:
        # Ensure pesadas directory exists
        pesadas_dir = os.path.join(os.getcwd(), "pesadas")
        os.makedirs(pesadas_dir, exist_ok=True)

        # Generate PDF in pesadas folder
        filename = os.path.join(pesadas_dir, f"ticket_compra_{compra_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        print(f"DEBUG: Generando PDF con {copies} copias para Compra {compra_id}")
        crear_pdf_recibo(datos, filename, tipo_recibo="Compra", copies=copies)
        print(f"DEBUG: PDF generado exitosamente: {filename}")
        
        # On Windows, try to print directly
        if platform.system() == "Windows":
            print(f"DEBUG: Intentando imprimir archivo: {filename} con {copies} copias")
            try:
                _try_print_file_windows(filename, copies=copies)
                print(f"DEBUG: Archivo enviado a impresora con {copies} copias")
                return JSONResponse(content={"status": "success", "message": "Ticket guardado en Pesadas e impreso"})
            except Exception as print_error:
                print(f"WARN: Error al imprimir, devolviendo PDF: {print_error}")
        
        # On Linux or if Windows printing failed, return PDF to browser
        print(f"DEBUG: Devolviendo PDF al navegador para impresión manual ({copies} copias)")
        return FileResponse(
            path=filename,
            media_type="application/pdf",
            filename=f"ticket_compra_{compra_id}.pdf",
            headers={
                "X-Copies-Requested": str(copies),
                "Content-Disposition": f"inline; filename=ticket_compra_{compra_id}.pdf"
            }
        )

    except Exception as e:
        # Log the error and raise an HTTPException
        print(f"ERROR generating/printing PDF for Compra {compra_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")

# Revert path parameter and type hint to int
@app.get("/compras/{compra_id}/guardar")
async def guardar_compra_pdf(compra_id: int, date: Optional[str] = None, current_user: UserInDB = Depends(has_role(["admin", "lect"]))):
    """Generate and save PDF for a specific compra entry."""
    datos = None
    should_upsert = True

    if compra_id in compras_entries:
        datos = [compras_entries[compra_id]]
    else:
        if date:
            try:
                entries = daily_excel_logger.load_data_by_date(date)
                compras_for_date = entries.get("Compra", [])
                found = next((e for e in compras_for_date if int(e.get("id")) == int(compra_id)), None)
                if found:
                    datos = [found]
                    should_upsert = False
                else:
                    raise HTTPException(status_code=404, detail="Compra no encontrada en la fecha solicitada")
            except HTTPException:
                raise
            except Exception as e:
                print(f"Error cargando Compra {compra_id} para la fecha {date}: {e}")
                raise HTTPException(status_code=500, detail=f"Error cargando datos: {e}")
        else:
            raise HTTPException(status_code=404, detail="Compra no encontrada")

    # If it's today's entry and in-memory, try to ensure saved to Excel
    if should_upsert and datos and compra_id in compras_entries:
        try:
            entry_dict = compras_entries[compra_id]
            data_row = [
                entry_dict.get("id"),
                "Compra",
                entry_dict.get("proveedor", ""),
                entry_dict.get("mercaderia", ""),
                entry_dict.get("bruto"),
                entry_dict.get("tara"),
                entry_dict.get("merma"),
                entry_dict.get("neto"),
                entry_dict.get("precio_kg"),
                entry_dict.get("importe"),
                entry_dict.get("chofer", ""),
                entry_dict.get("patente", ""),
                "", # Incoterm (solo aplica a Ventas)
                entry_dict.get("fecha", ""),
                entry_dict.get("hora_ingreso", ""),
                entry_dict.get("hora_salida", ""),
                "", # Remito (no aplica a Compras)
                entry_dict.get("observaciones", "")
            ]
            data_row_cleaned = ["" if v is None else v for v in data_row]
            daily_excel_logger.upsert_data(entry_id=compra_id, entry_type="Compra", data_row=data_row_cleaned)
        except Exception as e:
            print(f"Error saving Compra {compra_id} before generating PDF: {e}")
            raise HTTPException(status_code=500, detail=_format_save_error(e))

    # Define the directory and filename
    if date and not should_upsert:
        save_dir = get_pesadas_folder_for_date(date)
    else:
        save_dir = get_daily_pesadas_folder()

    filename = os.path.join(save_dir, f"compra_{compra_id}.pdf")

    try:
        crear_pdf_recibo(datos, filename, tipo_recibo="Compra")
        
        return JSONResponse(content={"status": "success", "message": f"Ticket guardado en {filename}"})

    except Exception as e:
        # Log the error and raise an HTTPException
        print(f"Error saving PDF for Compra {compra_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al guardar PDF para Compra: {str(e)}")


# --- Ventas Endpoints ---
@app.get("/ventas", response_model=List[Venta])
async def read_ventas_entries(
    search: Optional[str] = None,
    date: Optional[str] = None,
    current_user: UserInDB = Depends(has_role(["admin", "lect"]))
):
    """
    Retrieve venta entries from a specific date sheet in Excel,
    with optional filtering.
    """
    # If no date is provided, default to today's date in YYYY-MM-DD format
    target_date_str = date if date else datetime.now().strftime("%Y-%m-%d")

    # Load data from the specific sheet
    all_data_for_date = daily_excel_logger.load_data_by_date(target_date_str)
    filtered_entries = all_data_for_date.get("Venta", [])

    # Filter by search term on the loaded data
    if search:
        search_term = search.lower()
        filtered_entries = [
            entry for entry in filtered_entries
            if search_term in str(entry.get("cliente", "")).lower() or \
               search_term in str(entry.get("mercaderia", "")).lower() or \
               search_term in str(entry.get("transporte", "")).lower() or \
               search_term in str(entry.get("patente", "")).lower()
        ]
        
    return filtered_entries

@app.post("/ventas", response_model=Venta)
async def create_venta_entry(venta_data: Venta, current_user: UserInDB = Depends(has_role(["admin"]))):
    """Create a new venta entry. This will always be for the CURRENT day."""
    global venta_counter, ventas_entries

    # --- Recalculate counter based on current day's sheet to avoid ID conflicts ---
    try:
        todays_data = daily_excel_logger.load_daily_data()
        todays_ventas = {entry["id"]: entry for entry in todays_data.get("Venta", []) if entry.get("id") is not None}
        venta_counter = max(todays_ventas.keys()) if todays_ventas else 0
    except Exception as e:
        print(f"Could not recalculate venta_counter, defaulting to in-memory. Error: {e}")
    # --- End recalculation ---

    venta_counter += 1
    new_id = venta_counter # Use simple integer ID
    venta_data.id = new_id
    venta_data.fecha = get_current_date()
    current_time = get_current_time()

    # Validate numeric fields first to avoid setting timestamps when empty strings are provided
    venta_data.bruto = validate_numeric(venta_data.bruto, 'bruto')
    venta_data.tara = validate_numeric(venta_data.tara, 'tara')
    venta_data.merma = validate_numeric(venta_data.merma, 'merma')
    venta_data.precio_kg = validate_numeric(venta_data.precio_kg, 'precio_kg')

    # Set times only when validated numeric values are present
    if venta_data.bruto is not None:
        venta_data.hora_ingreso = current_time
    if venta_data.tara is not None:
        venta_data.hora_salida = current_time

    venta_data.neto = calculate_neto(venta_data.bruto, venta_data.tara, venta_data.merma)
    venta_data.importe = calculate_importe(venta_data.neto, venta_data.precio_kg)

    # Sanitize string fields and ensure mercaderia is stored correctly
    entry_dict = venta_data.dict()
    entry_dict["mercaderia"] = sanitize_str(entry_dict.get("mercaderia"))
    entry_dict["cliente"] = sanitize_str(entry_dict.get("cliente"))
    entry_dict["transporte"] = sanitize_str(entry_dict.get("transporte"))
    entry_dict["patente"] = sanitize_str(entry_dict.get("patente"), max_len=20)
    # Store incoterm (CIF/FOB) if provided; keep as short token
    try:
        inc = entry_dict.get("incoterm")
        if inc:
            inc = sanitize_str(str(inc), max_len=10).upper()
            if inc not in ("CIF", "FOB"):
                inc = None
        entry_dict["incoterm"] = inc
    except Exception:
        entry_dict["incoterm"] = None
    entry_dict["observaciones"] = sanitize_str(entry_dict.get("observaciones"), max_len=1000)
    # Normalizar remito a entero (o None)
    try:
        rem = entry_dict.get("remito")
        if rem in (None, ""):
            entry_dict["remito"] = None
        elif isinstance(rem, int):
            pass
        else:
            entry_dict["remito"] = int(float(rem))
    except Exception:
        entry_dict["remito"] = None

    # Use the integer ID as the key for the dictionary
    ventas_entries[new_id] = entry_dict 

    # --- Upsert to Excel ---
    try:
        # Prepare data row according to new daily_excel_logger.HEADERS
        data_row = [
            entry_dict.get("id"), # Registro ID
            "Venta", # Tipo Operación
            entry_dict.get("cliente", ""), # Contraparte
            entry_dict.get("mercaderia", ""), # Producto
            entry_dict.get("bruto"), # Peso Bruto (kg)
            entry_dict.get("tara"), # Peso Tara (kg)
            entry_dict.get("merma"), # Merma (kg)
            entry_dict.get("neto"), # Peso Neto (kg)
            entry_dict.get("precio_kg"), # Precio x Kg
            entry_dict.get("importe"), # Importe
            entry_dict.get("transporte", ""), # Transporte
            entry_dict.get("patente", ""), # Patente
            entry_dict.get("incoterm", ""), # Incoterm (CIF/FOB) - new column
            entry_dict.get("fecha", ""), # Fecha Operación
            entry_dict.get("hora_ingreso", ""), # Hora Ingreso
            entry_dict.get("hora_salida", ""), # Hora Salida
            entry_dict.get("remito", ""), # Remito (nuevo)
            entry_dict.get("observaciones", "") # Observaciones - Added
        ]
        # Convert None to empty string for Excel compatibility
        data_row_cleaned = ["" if v is None else v for v in data_row]
        # Use the integer ID and type for upserting
        daily_excel_logger.upsert_data(entry_id=new_id, entry_type="Venta", data_row=data_row_cleaned)
        # Verify write by reloading today's data and checking the ID exists
        reloaded = daily_excel_logger.load_daily_data()
        todays_ventas = {entry["id"]: entry for entry in reloaded.get("Venta", []) if entry.get("id") is not None}
        if new_id not in todays_ventas:
            logger_msg = f"Post-upsert verification failed: Venta {new_id} not found in today's sheet."
            print(logger_msg)
            raise HTTPException(status_code=500, detail=logger_msg)
    except Exception as e:
        # Log the error and raise an HTTPException
        print(f"Error upserting Venta {new_id} to Excel: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving venta entry to Excel: {e}")

    await notify_clients("venta")
    # Return using the integer ID
    return ventas_entries[new_id]

# Revert path parameter and type hint to int

@app.put("/ventas/{venta_id}", response_model=Venta)
async def update_venta_entry(venta_id: int, venta_data: VentaUpdate, current_user: UserInDB = Depends(has_role(["admin"]))):
    """Update an existing venta entry."""
    if venta_id not in ventas_entries:
        # Fallback: intentar cargar la venta del día actual desde Excel
        try:
            todays = daily_excel_logger.load_daily_data().get("Venta", [])
            found = next((e for e in todays if int(e.get("id") or -1) == int(venta_id)), None)
            if found:
                ventas_entries[venta_id] = found
            else:
                raise HTTPException(status_code=404, detail="Venta no encontrada (puede ser de otra fecha)")
        except HTTPException:
            raise
        except Exception as e:
            print(f"Fallback load for Venta {venta_id} failed: {e}")
            raise HTTPException(status_code=404, detail="Venta no encontrada")

    current_entry = ventas_entries[venta_id]
    update_data = venta_data.dict(exclude_unset=True)

    # Preserve existing timestamps unless new valid weights are added
    if "bruto" in update_data:
        validated_bruto = validate_numeric(update_data.get("bruto"), 'bruto')
        update_data["bruto"] = validated_bruto
        if validated_bruto is not None and current_entry.get("hora_ingreso") is None:
            update_data["hora_ingreso"] = get_current_time()
        else:
            update_data["hora_ingreso"] = current_entry.get("hora_ingreso")
    else:
        update_data["hora_ingreso"] = current_entry.get("hora_ingreso")

    if "tara" in update_data:
        validated_tara = validate_numeric(update_data.get("tara"), 'tara')
        update_data["tara"] = validated_tara
        if validated_tara is not None and current_entry.get("hora_salida") is None:
            update_data["hora_salida"] = get_current_time()
        else:
            update_data["hora_salida"] = current_entry.get("hora_salida")
    else:
        update_data["hora_salida"] = current_entry.get("hora_salida")

    # Validate other numeric fields in the update payload if present
    if "merma" in update_data:
        update_data["merma"] = validate_numeric(update_data.get("merma"), 'merma')
    if "precio_kg" in update_data:
        update_data["precio_kg"] = validate_numeric(update_data.get("precio_kg"), 'precio_kg')
    # Normalizar remito en updates
    if "remito" in update_data:
        try:
            rem = update_data.get("remito")
            if rem in (None, ""):
                update_data["remito"] = None
            elif isinstance(rem, int):
                pass
            else:
                update_data["remito"] = int(float(rem))
        except Exception:
            update_data["remito"] = current_entry.get("remito")

    update_data["fecha"] = current_entry.get("fecha")
    update_data["id"] = venta_id

    merged_data = {**current_entry, **update_data}
    merged_data["neto"] = calculate_neto(merged_data.get("bruto"), merged_data.get("tara"), merged_data.get("merma"))
    merged_data["importe"] = calculate_importe(merged_data.get("neto"), merged_data.get("precio_kg"))

    if "mercaderia" in merged_data and merged_data["mercaderia"] is None:
        merged_data["mercaderia"] = ""
    # Normalize incoterm token if present
    try:
        inc = merged_data.get("incoterm")
        if inc:
            inc = sanitize_str(str(inc), max_len=10).upper()
            if inc not in ("CIF", "FOB"):
                inc = None
        merged_data["incoterm"] = inc
    except Exception:
        merged_data["incoterm"] = current_entry.get("incoterm")

    ventas_entries[venta_id] = merged_data
    
    try:
        data_row = [
            merged_data.get("id"),
            "Venta",
            merged_data.get("cliente", ""),
            merged_data.get("mercaderia", ""),
            merged_data.get("bruto"),
            merged_data.get("tara"),
            merged_data.get("merma"),
            merged_data.get("neto"),
            merged_data.get("precio_kg"),
            merged_data.get("importe"),
            merged_data.get("transporte", ""),
            merged_data.get("patente", ""),
            merged_data.get("incoterm", ""),
            merged_data.get("fecha", ""),
            merged_data.get("hora_ingreso", ""),
            merged_data.get("hora_salida", ""),
            merged_data.get("remito", ""),
            merged_data.get("observaciones", "")
        ]
        data_row_cleaned = ["" if v is None else v for v in data_row]
        daily_excel_logger.upsert_data(entry_id=venta_id, entry_type="Venta", data_row=data_row_cleaned)
    except Exception as e:
        print(f"Error upserting Venta {venta_id} to Excel: {e}")
        raise HTTPException(status_code=500, detail=_format_save_error(e))

    # Verify write by reloading today's data and checking the ID exists (post-update read-back)
    try:
        reloaded = daily_excel_logger.load_daily_data()
        todays_ventas = {entry["id"]: entry for entry in reloaded.get("Venta", []) if entry.get("id") is not None}
        if venta_id not in todays_ventas:
            logger_msg = f"Post-update verification failed: Venta {venta_id} not found in today's sheet."
            print(logger_msg)
            raise HTTPException(status_code=500, detail=logger_msg)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error verifying updated Venta {venta_id}: {e}")
        raise HTTPException(status_code=500, detail=_format_save_error(e))

    await notify_clients("venta")
    return ventas_entries[venta_id]

# Revert path parameter and type hint to int
@app.delete("/ventas/{venta_id}")
async def delete_venta_entry(venta_id: int, current_user: UserInDB = Depends(has_role(["admin"]))):
    """Delete a venta entry."""
    # Use integer ID for lookup
    if venta_id not in ventas_entries:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    # --- Delete from Excel ---
    try:
        # Use integer ID and type for deletion
        daily_excel_logger.delete_data(entry_id=venta_id, entry_type="Venta")
    except Exception as e:
        # Log the error and raise an HTTPException
        print(f"Error deleting Venta {venta_id} from Excel: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting venta entry from Excel: {e}")

    # Use integer ID to delete from memory
    del ventas_entries[venta_id]
    await notify_clients("venta")
    return {"message": "Venta eliminada correctamente"}

# Revert path parameter and type hint to int
@app.get("/ventas/{venta_id}/imprimir")
async def imprimir_venta_pdf(venta_id: int, copies: int = 2, date: Optional[str] = None, current_user: UserInDB = Depends(has_role(["admin", "lect"]))):
    """Generate and return PDF for a specific venta entry (Client-side printing)."""
    
    files_to_clean = []
    datos = None
    should_upsert = True

    if venta_id in ventas_entries:
        datos = [ventas_entries[venta_id]]
    else:
        if date:
            try:
                entries = daily_excel_logger.load_data_by_date(date)
                ventas_for_date = entries.get("Venta", [])
                found = next((e for e in ventas_for_date if int(e.get("id")) == int(venta_id)), None)
                if found:
                    datos = [found]
                    should_upsert = False
                else:
                    raise HTTPException(status_code=404, detail="Venta no encontrada en la fecha solicitada")
            except HTTPException:
                raise
            except Exception as e:
                print(f"Error cargando Venta {venta_id} para la fecha {date}: {e}")
                raise HTTPException(status_code=500, detail=f"Error cargando datos: {e}")
        else:
            raise HTTPException(status_code=404, detail="Venta no encontrada")

    # If this is today's record and we have it in memory, ensure it's saved before printing
    if should_upsert and datos and venta_id in ventas_entries:
        try:
            entry_dict = ventas_entries[venta_id]
            data_row = [
                entry_dict.get("id"),
                "Venta",
                entry_dict.get("cliente", ""),
                entry_dict.get("mercaderia", ""),
                entry_dict.get("bruto"),
                entry_dict.get("tara"),
                entry_dict.get("merma"),
                entry_dict.get("neto"),
                entry_dict.get("precio_kg"),
                entry_dict.get("importe"),
                entry_dict.get("transporte", ""),
                entry_dict.get("patente", ""),
                entry_dict.get("incoterm", ""),
                entry_dict.get("fecha", ""),
                entry_dict.get("hora_ingreso", ""),
                entry_dict.get("hora_salida", ""),
                entry_dict.get("remito", ""),
                entry_dict.get("observaciones", "")
            ]
            data_row_cleaned = ["" if v is None else v for v in data_row]
            daily_excel_logger.upsert_data(entry_id=venta_id, entry_type="Venta", data_row=data_row_cleaned)
        except Exception as e:
            print(f"Error saving Venta {venta_id} before printing: {e}")
            raise HTTPException(status_code=500, detail=_format_save_error(e))

    try:
        # Ensure pesadas directory exists
        pesadas_dir = os.path.join(os.getcwd(), "pesadas")
        os.makedirs(pesadas_dir, exist_ok=True)

        # Generate PDF in pesadas folder
        filename = os.path.join(pesadas_dir, f"ticket_venta_{venta_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        print(f"DEBUG: Generando PDF con {copies} copias para Venta {venta_id}")
        crear_pdf_recibo(datos, filename, tipo_recibo="Venta", copies=copies)
        print(f"DEBUG: PDF generado exitosamente: {filename}")
        
        # On Windows, try to print directly
        if platform.system() == "Windows":
            print(f"DEBUG: Intentando imprimir archivo: {filename} con {copies} copias")
            try:
                _try_print_file_windows(filename, copies=copies)
                print(f"DEBUG: Archivo enviado a impresora con {copies} copias")
                return JSONResponse(content={"status": "success", "message": "Ticket guardado en Pesadas e impreso"})
            except Exception as print_error:
                print(f"WARN: Error al imprimir, devolviendo PDF: {print_error}")
        
        # On Linux or if Windows printing failed, return PDF to browser
        print(f"DEBUG: Devolviendo PDF al navegador para impresión manual ({copies} copias)")
        return FileResponse(
            path=filename,
            media_type="application/pdf",
            filename=f"ticket_venta_{venta_id}.pdf",
            headers={
                "X-Copies-Requested": str(copies),
                "Content-Disposition": f"inline; filename=ticket_venta_{venta_id}.pdf"
            }
        )

    except Exception as e:
        # Log the error and raise an HTTPException
        print(f"ERROR generating/printing PDF for Venta {venta_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")

# Revert path parameter and type hint to int
@app.get("/ventas/{venta_id}/guardar")
async def guardar_venta_pdf(venta_id: int, date: Optional[str] = None, current_user: UserInDB = Depends(has_role(["admin", "lect"]))):
    """Generate and save PDF for a specific venta entry. Accepts optional `date` (YYYY-MM-DD) for historical records."""
    datos = None
    should_upsert = True

    if venta_id in ventas_entries:
        datos = [ventas_entries[venta_id]]
    else:
        if date:
            try:
                entries = daily_excel_logger.load_data_by_date(date)
                ventas_for_date = entries.get("Venta", [])
                found = next((e for e in ventas_for_date if int(e.get("id")) == int(venta_id)), None)
                if found:
                    datos = [found]
                    should_upsert = False
                else:
                    raise HTTPException(status_code=404, detail="Venta no encontrada en la fecha solicitada")
            except HTTPException:
                raise
            except Exception as e:
                print(f"Error cargando Venta {venta_id} para la fecha {date}: {e}")
                raise HTTPException(status_code=500, detail=f"Error cargando datos: {e}")
        else:
            raise HTTPException(status_code=404, detail="Venta no encontrada")

    # If it's today's entry and in-memory, try to ensure saved to Excel
    if should_upsert and datos and venta_id in ventas_entries:
        try:
            entry_dict = ventas_entries[venta_id]
            data_row = [
                entry_dict.get("id"),
                "Venta",
                entry_dict.get("cliente", ""),
                entry_dict.get("mercaderia", ""),
                entry_dict.get("bruto"),
                entry_dict.get("tara"),
                entry_dict.get("merma"),
                entry_dict.get("neto"),
                entry_dict.get("precio_kg"),
                entry_dict.get("importe"),
                entry_dict.get("transporte", ""),
                entry_dict.get("patente", ""),
                entry_dict.get("incoterm", ""),
                entry_dict.get("fecha", ""),
                entry_dict.get("hora_ingreso", ""),
                entry_dict.get("hora_salida", ""),
                entry_dict.get("remito", ""),
                entry_dict.get("observaciones", "")
            ]
            data_row_cleaned = ["" if v is None else v for v in data_row]
            daily_excel_logger.upsert_data(entry_id=venta_id, entry_type="Venta", data_row=data_row_cleaned)
        except Exception as e:
            print(f"Error saving Venta {venta_id} before generating PDF: {e}")
            raise HTTPException(status_code=500, detail=_format_save_error(e))

    # Define the directory and filename
    if date and not should_upsert:
        save_dir = get_pesadas_folder_for_date(date)
    else:
        save_dir = get_daily_pesadas_folder()

    filename = os.path.join(save_dir, f"venta_{venta_id}.pdf")

    try:
        crear_pdf_recibo(datos, filename, tipo_recibo="Venta")
        
        return JSONResponse(content={"status": "success", "message": f"Ticket guardado en {filename}"})

    except Exception as e:
        # Log the error and raise an HTTPException
        print(f"Error saving PDF for Venta {venta_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al guardar PDF para Venta: {str(e)}")


# --- Endpoint for Printing Complete Report ---
@app.get("/imprimir/todo")
async def imprimir_planilla_completa(current_user: UserInDB = Depends(has_role(["admin", "lect"]))):
    """Generate and return a complete PDF report with both compras and ventas for client-side viewing/printing."""
    # Prepare data combining both compras and ventas
    compras_data = [{"tipo": "Compra", **entry} for entry in compras_entries.values()]
    ventas_data = [{"tipo": "Venta", **entry} for entry in ventas_entries.values()]
    todos_datos = compras_data + ventas_data

    # Sort by date and time
    todos_datos.sort(key=lambda x: (x.get("fecha") or "", x.get("hora_ingreso") or ""), reverse=True)

    # Generate PDF in Planilla directory for persistence
    try:
        planilla_folder = get_planilla_folder_for_today()
        filename = os.path.join(planilla_folder, f"planilla_completa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        print(f"DEBUG: Generando planilla completa en: {filename}")
        
        generar_planilla(todos_datos, filename)
        print(f"DEBUG: Planilla generada exitosamente")
        
        # On Windows, try to print directly
        if platform.system() == "Windows":
            print(f"DEBUG: Intentando imprimir planilla completa")
            try:
                _try_print_file_windows(filename, copies=1)
                print(f"DEBUG: Planilla enviada a impresora")
                return JSONResponse(content={"status": "success", "message": "Planilla guardada en Planilla/ e impresa"})
            except Exception as print_error:
                print(f"WARN: Error al imprimir, devolviendo PDF: {print_error}")
        
        # On Linux or if Windows printing failed, return PDF to browser
        print(f"DEBUG: Devolviendo PDF al navegador para visualización/impresión")
        return FileResponse(
            path=filename,
            media_type="application/pdf",
            filename=f"planilla_completa.pdf",
            headers={
                "Content-Disposition": f"inline; filename=planilla_completa.pdf"
            }
        )
    except Exception as e:
        # Log the error and raise an HTTPException
        print(f"ERROR generating PDF for complete report: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")


@app.get("/imprimir/compras")
async def imprimir_planilla_compras(current_user: UserInDB = Depends(has_role(["admin", "lect"]))):
    """Generate and return a PDF report with only compras for client-side viewing/printing."""
    # Prepare data with only compras
    compras_data = [{"tipo": "Compra", **entry} for entry in compras_entries.values()]

    # Sort by date and time
    compras_data.sort(key=lambda x: (x.get("fecha") or "", x.get("hora_ingreso") or ""), reverse=True)

    # Generate PDF in Planilla directory for persistence
    try:
        planilla_folder = get_planilla_folder_for_today()
        filename = os.path.join(planilla_folder, f"planilla_compras_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        print(f"DEBUG: Generando planilla de compras en: {filename}")
        
        generar_planilla(compras_data, filename)
        print(f"DEBUG: Planilla de compras generada exitosamente")
        
        # On Windows, try to print directly
        if platform.system() == "Windows":
            print(f"DEBUG: Intentando imprimir planilla de compras")
            try:
                _try_print_file_windows(filename, copies=1)
                print(f"DEBUG: Planilla enviada a impresora")
                return JSONResponse(content={"status": "success", "message": "Planilla de compras guardada en Planilla/ e impresa"})
            except Exception as print_error:
                print(f"WARN: Error al imprimir, devolviendo PDF: {print_error}")
        
        # On Linux or if Windows printing failed, return PDF to browser
        print(f"DEBUG: Devolviendo PDF al navegador para visualización/impresión")
        return FileResponse(
            path=filename,
            media_type="application/pdf",
            filename=f"planilla_compras.pdf",
            headers={
                "Content-Disposition": f"inline; filename=planilla_compras.pdf"
            }
        )
    except Exception as e:
        # Log the error and raise an HTTPException
        print(f"ERROR generating PDF for compras report: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")


@app.get("/imprimir/ventas")
async def imprimir_planilla_ventas(current_user: UserInDB = Depends(has_role(["admin", "lect"]))):
    """Generate and return a PDF report with only ventas for client-side viewing/printing."""
    # Prepare data with only ventas
    ventas_data = [{"tipo": "Venta", **entry} for entry in ventas_entries.values()]

    # Sort by date and time
    ventas_data.sort(key=lambda x: (x.get("fecha") or "", x.get("hora_ingreso") or ""), reverse=True)

    # Generate PDF in Planilla directory for persistence
    try:
        planilla_folder = get_planilla_folder_for_today()
        filename = os.path.join(planilla_folder, f"planilla_ventas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        print(f"DEBUG: Generando planilla de ventas en: {filename}")
        
        generar_planilla(ventas_data, filename)
        print(f"DEBUG: Planilla de ventas generada exitosamente")
        
        # On Windows, try to print directly
        if platform.system() == "Windows":
            print(f"DEBUG: Intentando imprimir planilla de ventas")
            try:
                _try_print_file_windows(filename, copies=1)
                print(f"DEBUG: Planilla enviada a impresora")
                return JSONResponse(content={"status": "success", "message": "Planilla de ventas guardada en Planilla/ e impresa"})
            except Exception as print_error:
                print(f"WARN: Error al imprimir, devolviendo PDF: {print_error}")
        
        # On Linux or if Windows printing failed, return PDF to browser
        print(f"DEBUG: Devolviendo PDF al navegador para visualización/impresión")
        return FileResponse(
            path=filename,
            media_type="application/pdf",
            filename=f"planilla_ventas.pdf",
            headers={
                "Content-Disposition": f"inline; filename=planilla_ventas.pdf"
            }
        )
    except Exception as e:
        # Log the error and raise an HTTPException
        print(f"ERROR generating PDF for ventas report: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")

@app.get("/ver/planilla-completa")
async def ver_planilla_completa(current_user: UserInDB = Depends(has_role(["admin", "lect"]))):
    """View the complete PDF report with both compras and ventas."""
    # Prepare data combining both compras and ventas
    compras_data = [{"tipo": "Compra", **entry} for entry in compras_entries.values()]
    ventas_data = [{"tipo": "Venta", **entry} for entry in ventas_entries.values()]
    todos_datos = compras_data + ventas_data

    # Sort by date and time
    todos_datos.sort(key=lambda x: (x.get("fecha") or "", x.get("hora_ingreso") or ""), reverse=True)

    # Generate PDF in temp directory
    temp_pdf = os.path.join(tempfile.gettempdir(), f"planilla_unificada_{datetime.now().timestamp()}.pdf")
    try:
        generar_planilla(todos_datos, temp_pdf)
        
    # Stream the file to avoid file locking issues
        def iterfile():
            with open(temp_pdf, 'rb') as f:
                yield from f
            # Clean up after streaming
            if os.path.exists(temp_pdf):
                try:
                    os.remove(temp_pdf)
                except Exception as e:
                    print(f"Error limpiando archivo temporal: {e}")
                    
        return StreamingResponse(
            iterfile(),
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"}
        )
    except Exception as e:
        # Log the error and raise an HTTPException
        print(f"Error generating complete report for viewing: {e}")
        if os.path.exists(temp_pdf):
            try:
                os.remove(temp_pdf)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")

@app.get("/descargar/planilla-completa")
async def descargar_planilla_completa(current_user: UserInDB = Depends(has_role(["admin", "lect"]))):
    """Download the complete PDF report with both compras and ventas."""
    # Prepare data combining both compras and ventas
    compras_data = [{"tipo": "Compra", **entry} for entry in compras_entries.values()]
    ventas_data = [{"tipo": "Venta", **entry} for entry in ventas_entries.values()]
    todos_datos = compras_data + ventas_data

    # Sort by date and time
    todos_datos.sort(key=lambda x: (x.get("fecha") or "", x.get("hora_ingreso") or ""), reverse=True)

    # Generate PDF in Planilla/ directory with filename planilla-DD-MM.pdf
    try:
        # Ensure base Planilla folder exists at c:\Users\Usuario\Documents\app\Planilla
        planilla_base_folder = os.path.join("Planilla")
        if not os.path.exists(planilla_base_folder):
            os.makedirs(planilla_base_folder)

        # Filename as requested: planilla-dia-mes (use 2-digit day and month)
        dia = datetime.now().strftime('%d')
        mes = datetime.now().strftime('%m')
        desired_filename = f"planilla-{dia}-{mes}.pdf"
        planilla_filepath = os.path.join(planilla_base_folder, desired_filename)

        # Generate the PDF at the desired path (overwrites if exists)
        generar_planilla(todos_datos, planilla_filepath)

        # Stream the generated file with the desired download name
        def iterfile():
            with open(planilla_filepath, 'rb') as f:
                yield from f
            # Do not delete; keep the file saved as requested

        return StreamingResponse(
            iterfile(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=\"{desired_filename}\""}
        )
    except Exception as e:
        # Log the error and raise an HTTPException
        print(f"Error generating complete report for download: {e}")
    raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")

@app.get("/guardar/planilla-completa")
async def guardar_planilla_completa(current_user: UserInDB = Depends(has_role(["admin", "lect"]))):
    """Generate and save the complete PDF report on the server without triggering a browser download."""
    # Prepare data combining both compras and ventas
    compras_data = [{"tipo": "Compra", **entry} for entry in compras_entries.values()]
    ventas_data = [{"tipo": "Venta", **entry} for entry in ventas_entries.values()]
    todos_datos = compras_data + ventas_data

    # Sort by date and time
    todos_datos.sort(key=lambda x: (x.get("fecha") or "", x.get("hora_ingreso") or ""), reverse=True)

    try:
        # Ensure Planilla base folder exists
        planilla_base_folder = os.path.join("Planilla")
        if not os.path.exists(planilla_base_folder):
            os.makedirs(planilla_base_folder)

        dia = datetime.now().strftime('%d')
        mes = datetime.now().strftime('%m')
        desired_filename = f"planilla-{dia}-{mes}.pdf"
        planilla_filepath = os.path.join(planilla_base_folder, desired_filename)

        generar_planilla(todos_datos, planilla_filepath)

        return {"status": "success", "message": "Planilla guardada", "path": planilla_filepath, "filename": desired_filename}
    except Exception as e:
        print(f"Error al guardar planilla completa en servidor: {e}")
        raise HTTPException(status_code=500, detail=f"Error guardando planilla: {str(e)}")

@app.get("/descargar/planilla")
async def descargar_planilla_filtrada(
    type: str, search: str = "", date: str = "", current_user: UserInDB = Depends(has_role(["admin", "lect"]))
):
    """Descarga la planilla filtrada por tipo (compras/ventas/todo), búsqueda y fecha."""
    from tempfile import gettempdir
    from pdf_generator import generar_planilla
    import os
    from datetime import datetime
    import daily_excel_logger

    tipo = type.lower()
    fecha_str = date if date else datetime.now().strftime("%Y-%m-%d")
    all_data = daily_excel_logger.load_data_by_date(fecha_str)
    datos = []
    if tipo == "compras":
        # Asegurar que cada item tenga la clave 'tipo' requerida por el generador de PDF
        datos = [{"tipo": "Compra", **entry} for entry in all_data.get("Compra", [])]
    elif tipo == "ventas":
        # Asegurar que cada item tenga la clave 'tipo' requerida por el generador de PDF
        datos = [{"tipo": "Venta", **entry} for entry in all_data.get("Venta", [])]
    elif tipo == "todo":
        datos = [{"tipo": "Compra", **entry} for entry in all_data.get("Compra", [])] + [{"tipo": "Venta", **entry} for entry in all_data.get("Venta", [])]
    else:
        raise HTTPException(status_code=400, detail="Tipo debe ser 'compras', 'ventas' o 'todo'.")
    # Filtrar por búsqueda
    if search:
        search_term = search.lower()
        if tipo == "compras":
            datos = [entry for entry in datos if search_term in str(entry.get("proveedor", "")).lower() or search_term in str(entry.get("mercaderia", "")).lower() or search_term in str(entry.get("chofer", "")).lower() or search_term in str(entry.get("patente", "")).lower()]
        elif tipo == "ventas":
            datos = [entry for entry in datos if search_term in str(entry.get("cliente", "")).lower() or search_term in str(entry.get("mercaderia", "")).lower() or search_term in str(entry.get("transporte", "")).lower() or search_term in str(entry.get("patente", "")).lower()]
        elif tipo == "todo":
            datos = [entry for entry in datos if (
                (entry.get("tipo") == "Compra" and (
                    search_term in str(entry.get("proveedor", "")).lower() or search_term in str(entry.get("mercaderia", "")).lower() or search_term in str(entry.get("chofer", "")).lower() or search_term in str(entry.get("patente", "")).lower()
                )) or
                (entry.get("tipo") == "Venta" and (
                    search_term in str(entry.get("cliente", "")).lower() or search_term in str(entry.get("mercaderia", "")).lower() or search_term in str(entry.get("transporte", "")).lower() or search_term in str(entry.get("patente", "")).lower()
                ))
            )]
    # Generar PDF temporal
    temp_pdf = os.path.join(gettempdir(), f"planilla_{tipo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    generar_planilla(datos, temp_pdf)
    # Stream para descarga
    def iterfile():
        with open(temp_pdf, 'rb') as f:
            yield from f
        if os.path.exists(temp_pdf):
            try:
                os.remove(temp_pdf)
            except Exception:
                pass
    return StreamingResponse(
        iterfile(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=planilla_{tipo}.pdf"}
    )

# --- Dashboard Endpoint ---
class MaterialTotal(BaseModel):
    mercaderia: str
    total_kilos: float

class DashboardData(BaseModel):
    total_kilos_comprados: float
    total_kilos_vendidos: float
    balance_neto: float
    compras_por_material: List[MaterialTotal]

@app.get("/api/dashboard/data", response_model=DashboardData)
async def get_dashboard_data(
    start_date: str,
    end_date: str,
    current_user: UserInDB = Depends(has_role(["admin", "lect"]))
):
    """
    Calculates dashboard data for a given date range.
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        all_compras = []
        all_ventas = []
        
        current_date = start
        while current_date <= end:
            date_str = current_date.strftime("%Y-%m-%d")
            data_for_date = daily_excel_logger.load_data_by_date(date_str)
            all_compras.extend(data_for_date.get("Compra", []))
            all_ventas.extend(data_for_date.get("Venta", []))
            current_date += timedelta(days=1)
            
        total_comprados = sum(item.get("neto", 0) or 0 for item in all_compras)
        total_vendidos = sum(item.get("neto", 0) or 0 for item in all_ventas)
        balance = total_comprados - total_vendidos
        
        material_summary = {}
        for item in all_compras:
            material = item.get("mercaderia", "Desconocido")
            kilos = item.get("neto", 0) or 0
            material_summary[material] = material_summary.get(material, 0) + kilos
            
        compras_por_material = [
            MaterialTotal(mercaderia=material, total_kilos=kilos)
            for material, kilos in material_summary.items()
        ]
        
        return DashboardData(
            total_kilos_comprados=total_comprados,
            total_kilos_vendidos=total_vendidos,
            balance_neto=balance,
            compras_por_material=compras_por_material
        )
    except Exception as e:
        print(f"Error calculating dashboard data for range {start_date} to {end_date}: {e}")
        raise HTTPException(status_code=500, detail=f"Error calculating dashboard data: {str(e)}")


# --- Dashboard: Últimos 5 días ---
class DailyBalance(BaseModel):
    fecha: str  # YYYY-MM-DD
    balance_neto: float


@app.get("/api/dashboard/last5days", response_model=List[DailyBalance])
async def get_last_5_days_balance(end_date: Optional[str] = None, current_user: UserInDB = Depends(has_role(["admin", "lect"]))):
    """
    Devuelve el balance neto (Compras - Ventas) de los últimos 5 días, incluido hoy.
    El formato de fecha devuelto es YYYY-MM-DD.
    """
    try:
        # Si se especifica end_date (YYYY-MM-DD), usarlo como ancla; si no, hoy
        if end_date:
            try:
                anchor = datetime.strptime(end_date, "%Y-%m-%d").date()
            except Exception:
                anchor = datetime.now().date()
        else:
            anchor = datetime.now().date()
        results: List[DailyBalance] = []
        # Recorremos de más antiguo a más reciente para mostrar cronológicamente
        for delta in range(4, -1, -1):
            d = anchor - timedelta(days=delta)
            date_str = d.strftime("%Y-%m-%d")
            data_for_date = daily_excel_logger.load_data_by_date(date_str)
            compras = data_for_date.get("Compra", [])
            ventas = data_for_date.get("Venta", [])
            total_compras = sum(item.get("neto", 0) or 0 for item in compras)
            total_ventas = sum(item.get("neto", 0) or 0 for item in ventas)
            balance = float(total_compras) - float(total_ventas)
            results.append(DailyBalance(fecha=date_str, balance_neto=balance))

        return results
    except Exception as e:
        print(f"Error calculating last 5 days balance: {e}")
        raise HTTPException(status_code=500, detail=f"Error calculating last 5 days balance: {str(e)}")


# --- Dashboard: Últimos movimientos (compras + ventas) ---
class LastMove(BaseModel):
    id: Optional[int] = None
    tipo: str  # "compra" | "venta"
    fecha: str  # YYYY-MM-DD
    mercaderia: Optional[str] = None
    neto: Optional[float] = None
    tercero: Optional[str] = None
    proveedor: Optional[str] = None
    cliente: Optional[str] = None


@app.get("/api/dashboard/last-moves", response_model=List[LastMove])
async def get_last_moves(
    start_date: str,
    end_date: str,
    limit: int = 6,
    current_user: UserInDB = Depends(has_role(["admin", "lect"]))
):
    """
    Devuelve una lista combinada de los últimos movimientos (Compras y Ventas)
    dentro del rango [start_date, end_date], ordenados por fecha y hora descendente.

    - start_date, end_date: YYYY-MM-DD
    - limit: cantidad máxima de elementos a devolver (default 6)

    Campos devueltos por ítem (compatibles con el frontend):
    { id, tipo: 'compra'|'venta', fecha: 'YYYY-MM-DD', mercaderia, neto, tercero, proveedor|cliente }
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        results: List[Dict[str, Any]] = []

        current = start
        while current <= end:
            ymd = current.strftime("%Y-%m-%d")
            data_for_date = daily_excel_logger.load_data_by_date(ymd)

            # Compras
            for it in data_for_date.get("Compra", []) or []:
                # Elegir una hora de referencia para ordenar (preferimos hora_salida si existe, sino ingreso)
                hora = (it.get("hora_salida") or it.get("hora_ingreso") or "00:00")
                # Normalizar HH:MM
                try:
                    hh, mm = (hora.split(":") + ["0"])[:2]
                    ts = datetime.strptime(f"{ymd} {int(hh):02d}:{int(mm):02d}", "%Y-%m-%d %H:%M")
                except Exception:
                    ts = datetime.strptime(f"{ymd} 00:00", "%Y-%m-%d %H:%M")
                move = {
                    "id": it.get("id"),
                    "tipo": "compra",
                    "fecha": ymd,
                    "mercaderia": it.get("mercaderia"),
                    "neto": float(it.get("neto") or 0),
                    "tercero": it.get("proveedor") or "",
                    "proveedor": it.get("proveedor") or "",
                    # ts interno para ordenar, no se expone
                    "_ts": ts,
                }
                results.append(move)

            # Ventas
            for it in data_for_date.get("Venta", []) or []:
                hora = (it.get("hora_salida") or it.get("hora_ingreso") or "00:00")
                try:
                    hh, mm = (hora.split(":") + ["0"])[:2]
                    ts = datetime.strptime(f"{ymd} {int(hh):02d}:{int(mm):02d}", "%Y-%m-%d %H:%M")
                except Exception:
                    ts = datetime.strptime(f"{ymd} 00:00", "%Y-%m-%d %H:%M")
                move = {
                    "id": it.get("id"),
                    "tipo": "venta",
                    "fecha": ymd,
                    "mercaderia": it.get("mercaderia"),
                    "neto": float(it.get("neto") or 0),
                    "tercero": it.get("cliente") or "",
                    "cliente": it.get("cliente") or "",
                    "_ts": ts,
                }
                results.append(move)

            current += timedelta(days=1)

        # Ordenar por timestamp descendente
        results.sort(key=lambda x: x.get("_ts") or datetime.min, reverse=True)
        # Recortar
        results = results[:limit]
        # Quitar la clave interna _ts
        for r in results:
            r.pop("_ts", None)

        # Validación suave de tipos para el response_model
        last_moves = [LastMove(**r) for r in results]
        return last_moves

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error obteniendo últimos movimientos: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo últimos movimientos: {str(e)}")


# --- Backup Endpoint ---
@app.get("/backup")
async def create_backup(current_user: UserInDB = Depends(has_role(["admin", "lect"]))):
    """Create a backup of the daily log Excel file."""
    try:
        # Ensure the source file exists
        if not os.path.exists("daily_log.xlsx"):
            raise HTTPException(status_code=404, detail="daily_log.xlsx not found.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"daily_log_backup_{timestamp}.xlsx"
        backup_folder = get_daily_backup_folder_for_today()
        backup_path = os.path.join(backup_folder, backup_filename)

        # Copy the file
        import shutil
        shutil.copy2("daily_log.xlsx", backup_path)

        return {"status": "success", "message": f"Backup created: {os.path.join(backup_folder, backup_filename)}"}

    except Exception as e:
        print(f"Error creating backup: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating backup: {str(e)}")


# --- Static Files ---
# Determine the path to the static directory based on whether the app is bundled
import sys
import os

if getattr(sys, 'frozen', False):
    # Running in a bundled environment
    static_dir = os.path.join(sys._MEIPASS, 'static')
else:
    # Running in a normal Python environment
    static_dir = 'static'

# Mount static files last so API routes take precedence
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

# Explicitly run the app with uvicorn when executed directly
if __name__ == "__main__":
    # Open the default web browser only when running directly (avoid side-effects at import time)
    try:
        import webbrowser
        webbrowser.open("http://127.0.0.1:8001")
    except Exception:
        pass

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_config=None)
