"""Atlas worker shell."""

from atlas_worker.agent_execution import (
    AgentExecutionResult,
    PolicyProtectedDemoResult,
    SeededAgentRunSpec,
    SimpleAgentLoopRunner,
    build_demo_browser_runner,
    build_demo_model_gateway,
    build_seeded_execution_context,
    build_seeded_tool_registry,
    execute_policy_protected_demo_run,
    execute_policy_protected_demo_run_from_config,
    execute_seeded_agent_run,
    execute_seeded_agent_run_from_config,
)
from atlas_worker.tool_registry import (
    DuplicateToolError,
    PlaceholderToolExecutor,
    RegisteredTool,
    ToolRegistry,
    ToolRegistryError,
    UnknownToolError,
    build_phase4_tool_registry,
    build_phase4_tool_registry_with_browser,
)
from atlas_worker.browser_tool import BrowserToolExecutor
from atlas_worker.demo_browser import DeterministicDemoBrowserRunner
from atlas_worker.directory_tool import DirectoryLookupToolExecutor
from atlas_worker.doc_tool import DocumentLookupToolExecutor
from atlas_worker.identity_tool import IdentityToolExecutor
from atlas_worker.screenshot_tool import ScreenshotToolExecutor
from atlas_worker.ticket_tool import HelpdeskTicketToolExecutor
from atlas_worker.isolated_command_tool import (
    IsolatedCommandToolExecutor,
    isolated_command_tool_spec,
)

__all__ = [
    "BrowserToolExecutor",
    "AgentExecutionResult",
    "DirectoryLookupToolExecutor",
    "DeterministicDemoBrowserRunner",
    "DuplicateToolError",
    "DocumentLookupToolExecutor",
    "HelpdeskTicketToolExecutor",
    "IdentityToolExecutor",
    "IsolatedCommandToolExecutor",
    "PolicyProtectedDemoResult",
    "PlaceholderToolExecutor",
    "RegisteredTool",
    "SeededAgentRunSpec",
    "ScreenshotToolExecutor",
    "SimpleAgentLoopRunner",
    "ToolRegistry",
    "ToolRegistryError",
    "UnknownToolError",
    "build_demo_browser_runner",
    "build_demo_model_gateway",
    "build_phase4_tool_registry",
    "build_phase4_tool_registry_with_browser",
    "build_seeded_execution_context",
    "build_seeded_tool_registry",
    "execute_policy_protected_demo_run",
    "execute_policy_protected_demo_run_from_config",
    "execute_seeded_agent_run",
    "execute_seeded_agent_run_from_config",
    "isolated_command_tool_spec",
]
