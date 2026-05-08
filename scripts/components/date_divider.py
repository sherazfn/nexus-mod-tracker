"""Date navigation component."""


def date_nav() -> str:
    """
    Generate date navigation with prev/next buttons in pill style.

    Returns:
        HTML string for the date navigation
    """
    return """<div class="date-nav">
            <button class="date-nav-btn prev" onclick="prevDate()" aria-label="Previous date">
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 12L6 8l4-4"/></svg>
            </button>
            <div class="date-nav-center">
                <span class="date-nav-badge" style="display: none;"></span>
                <div class="date-nav-pill">
                    <span class="date-nav-current">Loading...</span>
                </div>
            </div>
            <button class="date-nav-btn next" onclick="nextDate()" aria-label="Next date">
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 12l4-4-4-4"/></svg>
            </button>
        </div>"""


def date_section(
    date_str: str,
    new_count: int,
    updated_count: int,
    content_new: str,
    content_updated: str,
    is_first: bool = False,
) -> str:
    """
    Generate a date section with tabs for new/updated.

    Args:
        date_str: Formatted date string
        new_count: Number of new mods for this date
        updated_count: Number of updated mods for this date
        content_new: HTML content for new mods
        content_updated: HTML content for updated mods
        is_first: Whether this is the first (active) section

    Returns:
        HTML string for the date section
    """
    active = "active" if is_first else ""

    # Default to the tab that has content (prefer "new" if both have content)
    default_tab = "new" if new_count > 0 else "updated"
    new_tab_active = "active" if default_tab == "new" else ""
    updated_tab_active = "active" if default_tab == "updated" else ""
    new_panel_active = "active" if default_tab == "new" else ""
    updated_panel_active = "active" if default_tab == "updated" else ""

    return f"""<div class="date-section {active}" data-date="{date_str}" data-new-count="{new_count}" data-updated-count="{updated_count}" data-default-tab="{default_tab}">
            <div class="date-content">
                <div class="tab-bar">
                    <div class="tab-group">
                        <button class="tab-button {new_tab_active}" data-tab="new" onclick="switchTab('new')">
                            <span>New</span>
                            <span class="tab-count">{new_count}</span>
                        </button>
                        <button class="tab-button {updated_tab_active}" data-tab="updated" onclick="switchTab('updated')">
                            <span>Updated</span>
                            <span class="tab-count">{updated_count}</span>
                        </button>
                    </div>
                </div>
                <div class="tab-panels">
                    <div class="tab-panel {new_panel_active}" data-panel="new">
                        <div class="mod-list">{content_new}</div>
                    </div>
                    <div class="tab-panel {updated_panel_active}" data-panel="updated">
                        <div class="mod-list">{content_updated}</div>
                    </div>
                </div>
            </div>
        </div>"""
