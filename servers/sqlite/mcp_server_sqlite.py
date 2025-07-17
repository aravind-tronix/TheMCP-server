from fastmcp import FastMCP
import sqlite3
from contextlib import closing
from pathlib import Path
import json
import logging
from config.config_loader import load_mcp_config

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="/mnt/d/linux/TheMCP/servers/sqlite/sqlite-mcp.log",
    filemode="a"
)
logger = logging.getLogger("mcp_server_sqlite")

# Load configuration
try:
    config = load_mcp_config()
    if "mcpServers" not in config or "sqlite-server" not in config["mcpServers"]:
        raise ValueError(
            f"Invalid mcpServers configuration: missing sqlite-server")
    server_config = config["mcpServers"]["sqlite-server"]
    if not all(key in server_config for key in ["serverName", "dbPath"]):
        raise ValueError(
            f"Missing serverName or dbPath in sqlite-server configuration")
    SERVER_NAME = server_config["serverName"]
    PORT = server_config.get("port")
    DB_PATH = server_config["dbPath"]
except Exception as e:
    logger.error(f"Failed to load configuration: {str(e)}")
    raise


class SqliteDatabase:
    def __init__(self, db_path: str):
        self.db_path = str(Path(db_path).expanduser())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize connection to the SQLite database."""
        logger.debug("Initializing database connection")
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            conn.close()

    def _execute_query(self, query: str, params: dict[str, any] | None = None) -> list[dict[str, any]]:
        """Execute a SQL query and return results as a list of dictionaries."""
        logger.debug(f"Executing query: {query}")
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                with closing(conn.cursor()) as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

                    if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER')):
                        conn.commit()
                        affected = cursor.rowcount
                        logger.debug(f"Write query affected {affected} rows")
                        return [{"affected_rows": affected}]

                    results = [dict(row) for row in cursor.fetchall()]
                    logger.debug(f"Read query returned {len(results)} rows")
                    return results
        except Exception as e:
            logger.error(f"Database error executing query: {e}")
            raise


# Initialize the MCP server
mcp = FastMCP(SERVER_NAME)
db = SqliteDatabase(DB_PATH)


@mcp.tool()
def read_query(query: str) -> str:
    """Execute a SELECT query on the candidates database and return results as JSON."""
    if not query.strip().upper().startswith("SELECT"):
        return json.dumps({"error": "Only SELECT queries are allowed for read_query"})
    try:
        results = db._execute_query(query)
        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def write_query(query: str) -> str:
    """Execute an INSERT, UPDATE, or DELETE query on the candidates database."""
    if query.strip().upper().startswith("SELECT"):
        return json.dumps({"error": "SELECT queries are not allowed for write_query"})
    try:
        results = db._execute_query(query)
        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_tables() -> str:
    """List all tables and views in the SQLite database."""
    try:
        results = db._execute_query(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")
        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def describe_table(table_name: str) -> str:
    """Get the schema information for a specific table or view."""
    try:
        results = db._execute_query(f"PRAGMA table_info({table_name})")
        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def update_candidate_asset(name: str, asset: str) -> str:
    """Add a physical asset to a candidate in the database."""
    try:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT physical_assets FROM candidates WHERE name = ?", (name,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return json.dumps({"error": f"Candidate {name} not found"})

            physical_assets = row[0].split(",") if row[0] else []
            if asset not in physical_assets:
                physical_assets.append(asset)
                cursor.execute("UPDATE candidates SET physical_assets = ? WHERE name = ?",
                               (",".join(physical_assets), name))
                conn.commit()
                conn.close()
                return json.dumps({"message": f"Added {asset} to {name}'s physical assets"})
            conn.close()
            return json.dumps({"message": f"{asset} already assigned to {name}"})
    except Exception as e:
        return json.dumps({"error": f"Error updating asset: {str(e)}"})


@mcp.tool()
def query_candidate_salary(name: str) -> str:
    """Query the candidate_salary_view for a candidate's details and salary structure."""
    try:
        results = db._execute_query(
            "SELECT * FROM candidate_salary_view WHERE name = ?", {"name": name})
        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    logger.info(f"Starting {SERVER_NAME} on http://localhost:{PORT}")
    mcp.run(transport="http", port=PORT, host="0.0.0.0")
