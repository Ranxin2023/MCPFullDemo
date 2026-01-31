from mcp.server.fastmcp import FastMCP
from credentials import CredentialManager
from tools.weather_tools import register_weather_tools
from tools.web_search_tool import register_web_tools
from tools.web_scrapy_tool import register_web_scrapy_tools
from tools.geo_tools import register_geo_tools
from tools.content_tools import register_content_tools
from tools.research_tools import register_research_tools
from tools.storage_tools import register_storage_tools
def build_server()->FastMCP:
    mcp = FastMCP("basic-mcp2")

    creds = CredentialManager()
    # Optional: validate only if you want to fail fast when launching
    # creds.validate_for_tools(["web_search"])

    register_weather_tools(mcp=mcp)
    register_web_tools(mcp=mcp, credentials=creds)
    register_geo_tools(mcp=mcp)
    register_web_scrapy_tools(mcp=mcp)
    register_content_tools(mcp=mcp)
    register_research_tools(mcp=mcp)
    register_storage_tools(mcp=mcp)
    return mcp

def main():
    mcp=build_server()
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()