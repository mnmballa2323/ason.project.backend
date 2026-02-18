"""
White-Label Branding System — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Per-tenant logos, colors, domain, email templates.
"""

import os
from typing import Any, Dict, Optional


# ============================================================================
#  BRANDING CONFIG
# ============================================================================

class BrandingConfig:
    """Per-tenant branding configuration."""

    # Default Liberty Center One branding
    DEFAULTS = {
        "company_name": "Ason Verification Platform",
        "tagline": "AI-Powered Claim Verification",
        "logo_url": "/static/logo.svg",
        "favicon_url": "/static/favicon.ico",

        # Color palette (CSS variables)
        "colors": {
            "primary": "#6366f1",          # Indigo
            "primary_hover": "#4f46e5",
            "secondary": "#06b6d4",        # Cyan
            "accent": "#f59e0b",           # Amber
            "background": "#0f172a",       # Slate-900
            "surface": "#1e293b",          # Slate-800
            "surface_hover": "#334155",    # Slate-700
            "text_primary": "#f8fafc",     # Slate-50
            "text_secondary": "#94a3b8",   # Slate-400
            "success": "#22c55e",
            "warning": "#eab308",
            "error": "#ef4444",
            "border": "#334155",
        },

        # Typography
        "fonts": {
            "heading": "'Inter', sans-serif",
            "body": "'Inter', sans-serif",
            "mono": "'JetBrains Mono', monospace",
        },

        # Layout
        "layout": {
            "sidebar_width": "260px",
            "header_height": "64px",
            "border_radius": "12px",
            "border_radius_sm": "8px",
        },

        # Custom CSS (injected into <head>)
        "custom_css": "",

        # Email
        "email": {
            "from_name": "Ason Verification",
            "from_address": "noreply@libertycenter.one",
            "footer_text": "Powered by Ason Verification Platform",
            "support_email": "support@libertycenter.one",
        },

        # Meta
        "meta": {
            "title_suffix": " — Ason Verification",
            "description": "AI-Powered Claim Verification Platform",
            "og_image": "/static/og-image.png",
        },

        # Features visibility
        "ui": {
            "show_powered_by": True,
            "show_documentation_link": True,
            "show_support_link": True,
            "custom_login_message": "",
            "custom_dashboard_banner": "",
        },
    }

    def __init__(self, tenant_id: str, overrides: Dict[str, Any] = None):
        self.tenant_id = tenant_id
        self._overrides = overrides or {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a branding value, falling back to defaults."""
        return self._overrides.get(key, self.DEFAULTS.get(key, default))

    def get_colors(self) -> Dict[str, str]:
        return {**self.DEFAULTS["colors"], **self._overrides.get("colors", {})}

    def get_fonts(self) -> Dict[str, str]:
        return {**self.DEFAULTS["fonts"], **self._overrides.get("fonts", {})}

    def to_css_variables(self) -> str:
        """Generate CSS custom properties from branding config."""
        colors = self.get_colors()
        fonts = self.get_fonts()
        layout = {**self.DEFAULTS["layout"], **self._overrides.get("layout", {})}

        lines = [":root {"]
        for key, value in colors.items():
            css_key = key.replace("_", "-")
            lines.append(f"  --color-{css_key}: {value};")
        for key, value in fonts.items():
            lines.append(f"  --font-{key}: {value};")
        for key, value in layout.items():
            css_key = key.replace("_", "-")
            lines.append(f"  --{css_key}: {value};")
        lines.append("}")

        custom_css = self._overrides.get("custom_css", "")
        if custom_css:
            lines.append(f"\n/* Tenant Custom CSS */\n{custom_css}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Export full branding config (merged defaults + overrides)."""
        merged = {}
        for key, value in self.DEFAULTS.items():
            if isinstance(value, dict):
                merged[key] = {**value, **self._overrides.get(key, {})}
            else:
                merged[key] = self._overrides.get(key, value)
        merged["tenant_id"] = self.tenant_id
        return merged

    def to_frontend_config(self) -> dict:
        """Export config for frontend consumption (safe, no secrets)."""
        return {
            "companyName": self.get("company_name"),
            "tagline": self.get("tagline"),
            "logoUrl": self.get("logo_url"),
            "faviconUrl": self.get("favicon_url"),
            "colors": self.get_colors(),
            "fonts": self.get_fonts(),
            "meta": {**self.DEFAULTS["meta"], **self._overrides.get("meta", {})},
            "ui": {**self.DEFAULTS["ui"], **self._overrides.get("ui", {})},
        }


# ============================================================================
#  BRANDING MANAGER
# ============================================================================

class BrandingManager:
    """Manages per-tenant branding configurations."""

    def __init__(self):
        self._configs: Dict[str, BrandingConfig] = {}
        self._default = BrandingConfig("default")

    def set_branding(self, tenant_id: str, overrides: Dict[str, Any]) -> BrandingConfig:
        """Set or update branding for a tenant."""
        config = BrandingConfig(tenant_id, overrides)
        self._configs[tenant_id] = config
        return config

    def get_branding(self, tenant_id: str) -> BrandingConfig:
        """Get branding config for a tenant (falls back to defaults)."""
        return self._configs.get(tenant_id, self._default)

    def get_css(self, tenant_id: str) -> str:
        """Get CSS variables for a tenant."""
        return self.get_branding(tenant_id).to_css_variables()

    def get_frontend_config(self, tenant_id: str) -> dict:
        """Get frontend-safe config for a tenant."""
        return self.get_branding(tenant_id).to_frontend_config()

    # --- Preset Themes ---
    PRESETS = {
        "dark_indigo": {
            "colors": {
                "primary": "#6366f1", "background": "#0f172a",
                "surface": "#1e293b", "text_primary": "#f8fafc",
            },
        },
        "light_corporate": {
            "colors": {
                "primary": "#2563eb", "background": "#ffffff",
                "surface": "#f8fafc", "text_primary": "#0f172a",
                "text_secondary": "#475569", "border": "#e2e8f0",
            },
        },
        "dark_emerald": {
            "colors": {
                "primary": "#10b981", "background": "#022c22",
                "surface": "#064e3b", "text_primary": "#ecfdf5",
            },
        },
        "government": {
            "colors": {
                "primary": "#1e3a5f", "background": "#0a1628",
                "surface": "#1a2744", "accent": "#d4a012",
                "text_primary": "#e2e8f0",
            },
            "ui": {"show_powered_by": False},
        },
    }

    def apply_preset(self, tenant_id: str, preset_name: str) -> Optional[BrandingConfig]:
        """Apply a branding preset to a tenant."""
        preset = self.PRESETS.get(preset_name)
        if not preset:
            return None
        return self.set_branding(tenant_id, preset)


# Global singleton
branding_manager = BrandingManager()
