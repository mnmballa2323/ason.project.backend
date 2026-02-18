"""
Plugin Architecture — Ason Verification Platform
Liberty Center One — Custom Verification Modules
ZERO EXTERNAL APIs. All plugins run locally.

Usage:
    1. Create a new plugin in plugins/ directory
    2. Implement the VerificationPlugin interface
    3. Register via plugins/__init__.py
    4. Plugin auto-discovered on startup
"""

import importlib
import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

logger = logging.getLogger("qwen.plugins")



class VerificationPlugin(ABC):
    """
    Base class for custom verification plugins.
    All plugins must implement verify() and metadata().
    """

    @abstractmethod
    def metadata(self) -> Dict[str, str]:
        """
        Return plugin metadata.
        Must include: name, version, description, license, author.
        License MUST be MIT or Apache-2.0.
        """
        ...

    @abstractmethod
    async def verify(self, claim: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify a claim using this plugin's domain-specific logic.

        Args:
            claim: The claim text to verify.
            context: Additional context (industry, evidence, etc.)

        Returns:
            Dict with keys: verdict (str), confidence (float), reasoning (str)
        """
        ...

    def pre_check(self) -> bool:
        """Optional: Run before verification. Return False to skip."""
        return True


class PluginRegistry:
    """
    Discovers and manages verification plugins.
    Auto-loads all plugins from the plugins/ directory.
    """

    def __init__(self):
        self._plugins: Dict[str, VerificationPlugin] = {}

    def register(self, plugin: VerificationPlugin):
        """Register a plugin instance."""
        meta = plugin.metadata()
        name = meta.get("name", "unknown")

        # License enforcement
        allowed_licenses = ["MIT", "Apache-2.0", "BSD-3-Clause", "ISC"]
        license_val = meta.get("license", "UNKNOWN")
        if license_val not in allowed_licenses:
            raise ValueError(
                f"Plugin '{name}' has license '{license_val}'. "
                f"Only {allowed_licenses} are permitted."
            )

        self._plugins[name] = plugin

    def discover(self, plugins_dir: str = "plugins"):
        """Auto-discover plugins from directory."""
        if not os.path.isdir(plugins_dir):
            return

        for filename in os.listdir(plugins_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                module_name = filename[:-3]
                try:
                    module = importlib.import_module(f"plugins.{module_name}")
                    if hasattr(module, "Plugin"):
                        plugin_instance = module.Plugin()
                        self.register(plugin_instance)
                except Exception as e:
                    logger.warning(f"Failed to load plugin {module_name}: {e}")

    def list_plugins(self) -> List[Dict[str, str]]:
        """List all registered plugins."""
        return [p.metadata() for p in self._plugins.values()]

    async def run_all(self, claim: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run all registered plugins against a claim."""
        results = []
        for name, plugin in self._plugins.items():
            if plugin.pre_check():
                try:
                    result = await plugin.verify(claim, context)
                    result["plugin"] = name
                    results.append(result)
                except Exception as e:
                    results.append({
                        "plugin": name,
                        "verdict": "ERROR",
                        "confidence": 0.0,
                        "reasoning": str(e),
                    })
        return results

    def get(self, name: str) -> Optional[VerificationPlugin]:
        """Get a specific plugin by name."""
        return self._plugins.get(name)


# --- Global Registry ---
plugin_registry = PluginRegistry()


# ============================================================
#  EXAMPLE PLUGIN (Automotive Safety Checker)
# ============================================================

class AutomotiveSafetyPlugin(VerificationPlugin):
    """Example plugin: checks automotive safety claims against known recall data."""

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "automotive-safety-checker",
            "version": "1.0.0",
            "description": "Cross-references claims against internal recall database",
            "license": "Apache-2.0",
            "author": "Liberty Center One",
        }

    async def verify(self, claim: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check claim against recall keywords."""
        recall_keywords = ["recall", "safety defect", "nhtsa", "fire risk", "brake failure"]
        flagged = any(kw in claim.lower() for kw in recall_keywords)

        return {
            "verdict": "FLAGGED" if flagged else "PASS",
            "confidence": 0.95 if flagged else 0.7,
            "reasoning": "Claim references known safety recall terminology" if flagged else "No safety flags detected",
        }


class PharmacologicalPlugin(VerificationPlugin):
    """Example plugin: checks pharma claims for GxP compliance markers."""

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "pharma-gxp-checker",
            "version": "1.0.0",
            "description": "Validates pharmaceutical claims against GxP compliance requirements",
            "license": "MIT",
            "author": "Liberty Center One",
        }

    async def verify(self, claim: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check for GxP compliance terminology."""
        gxp_terms = ["fda", "gmp", "clinical trial", "adverse event", "batch release", "21 cfr"]
        has_gxp = any(term in claim.lower() for term in gxp_terms)

        return {
            "verdict": "GXP_RELEVANT" if has_gxp else "STANDARD",
            "confidence": 0.9 if has_gxp else 0.6,
            "reasoning": "Claim contains GxP-regulated terminology" if has_gxp else "Standard claim, no GxP relevance",
        }


# Auto-register built-in plugins
plugin_registry.register(AutomotiveSafetyPlugin())
plugin_registry.register(PharmacologicalPlugin())
