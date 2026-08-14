import math
import os

import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Open-Loop Geothermal Screening Tool",
    page_icon="💧",
    layout="wide"
)


# ============================================================
# CONSTANTS
# ============================================================

GPM_PER_TON = 2.5

LIKE_WELL_SPACING_FT = 200
PRODUCTION_INJECTION_SEPARATION_FT = 1000

# Half of the required like-well spacing is included
# around the outside of the conceptual wellfield.
PERIMETER_BUFFER_FT = LIKE_WELL_SPACING_FT / 2

COST_PER_TON = 12500

# One redundant production well and one redundant injection well
# are included in each scenario.
REDUNDANT_WELLS_PER_TYPE = 1


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def calculate_required_well_count(peak_load_tons, well_yield_gpm):
    """
    Calculate the number of operating wells required to meet the
    estimated groundwater flow.

    Assumes:
        2.5 gpm = 1 ton

    Redundant wells are added separately.
    """

    total_required_flow_gpm = peak_load_tons * GPM_PER_TON

    if well_yield_gpm <= 0:
        return 0, total_required_flow_gpm

    required_wells = math.ceil(
        total_required_flow_gpm / well_yield_gpm
    )

    return required_wells, total_required_flow_gpm


def make_grid_coordinates(number_of_wells, spacing):
    """
    Create a compact, approximately square grid for one well group.
    """

    if number_of_wells <= 0:
        return []

    columns = math.ceil(math.sqrt(number_of_wells))
    rows = math.ceil(number_of_wells / columns)

    coordinates = []

    for i in range(number_of_wells):

        row = i // columns
        column = i % columns

        x = column * spacing
        y = row * spacing

        coordinates.append((x, y))

    return coordinates


def create_open_loop_layout(number_of_installed_wells):
    """
    Create conceptual production and injection well coordinates.

    The number passed to this function includes the redundant well.

    Production wells are placed in one compact grid and injection
    wells are placed to the right.

    The nearest production and injection wells are separated by at
    least 1,000 ft.

    A 100-ft perimeter buffer is added around the entire conceptual
    footprint.
    """

    production = make_grid_coordinates(
        number_of_installed_wells,
        LIKE_WELL_SPACING_FT
    )

    injection_local = make_grid_coordinates(
        number_of_installed_wells,
        LIKE_WELL_SPACING_FT
    )

    if not production:
        return [], [], 0, 0, 0

    production_max_x = max(
        x for x, y in production
    )

    injection_offset_x = (
        production_max_x
        + PRODUCTION_INJECTION_SEPARATION_FT
    )

    injection = [
        (x + injection_offset_x, y)
        for x, y in injection_local
    ]

    all_coordinates = production + injection

    min_x = min(x for x, y in all_coordinates)
    max_x = max(x for x, y in all_coordinates)

    min_y = min(y for x, y in all_coordinates)
    max_y = max(y for x, y in all_coordinates)

    field_width_ft = (
        max_x - min_x
        + 2 * PERIMETER_BUFFER_FT
    )

    field_height_ft = (
        max_y - min_y
        + 2 * PERIMETER_BUFFER_FT
    )

    field_area_sqft = (
        field_width_ft
        * field_height_ft
    )

    return (
        production,
        injection,
        field_width_ft,
        field_height_ft,
        field_area_sqft
    )


def choose_scale_length(field_width):
    """
    Select a clean graphical scale-bar length based on field size.
    """

    if field_width >= 5000:
        return 1000
    elif field_width >= 2500:
        return 500
    elif field_width >= 1200:
        return 200
    else:
        return 100


def add_scale_bar(
    ax,
    field_width,
    field_height,
    min_x_display,
    min_y_display
):
    """
    Add a graphical scale bar in the lower-left portion of the plot.
    """

    scale_length = choose_scale_length(field_width)

    x_start = (
        min_x_display
        + field_width * 0.05
    )

    y_start = (
        min_y_display
        + max(field_height * 0.08, 40)
    )

    tick_height = max(
        field_height * 0.025,
        12
    )

    ax.plot(
        [
            x_start,
            x_start + scale_length
        ],
        [
            y_start,
            y_start
        ],
        color="black",
        linewidth=3,
        zorder=5
    )

    ax.plot(
        [
            x_start,
            x_start
        ],
        [
            y_start - tick_height,
            y_start + tick_height
        ],
        color="black",
        linewidth=2,
        zorder=5
    )

    ax.plot(
        [
            x_start + scale_length,
            x_start + scale_length
        ],
        [
            y_start - tick_height,
            y_start + tick_height
        ],
        color="black",
        linewidth=2,
        zorder=5
    )

    ax.text(
        x_start + scale_length / 2,
        y_start + tick_height * 1.6,
        f"{scale_length:,} ft",
        ha="center",
        va="bottom",
        fontsize=9
    )


def get_marker_size(number_of_wells):
    """
    Reduce marker size automatically for larger wellfields.
    """

    if number_of_wells <= 10:
        return 85
    elif number_of_wells <= 25:
        return 65
    elif number_of_wells <= 50:
        return 48
    elif number_of_wells <= 100:
        return 34
    else:
        return 24


def get_figure_size(
    field_width_ft,
    field_height_ft
):
    """
    Adjust figure proportions based on the conceptual wellfield shape.

    This helps prevent figures from becoming excessively crowded as
    the number of wells increases.
    """

    if field_height_ft <= 0:
        return 10, 5

    aspect_ratio = (
        field_width_ft
        / field_height_ft
    )

    # Wider wellfields receive more horizontal space.
    figure_width = min(
        max(10, 7 + aspect_ratio * 1.5),
        15
    )

    # Taller fields receive more vertical space.
    figure_height = min(
        max(5.5, figure_width / max(aspect_ratio, 1.5)),
        9
    )

    return figure_width, figure_height


def create_wellfield_figure(
    number_of_installed_wells,
    required_wells,
    well_yield,
    scenario_name
):
    """
    Generate a conceptual production/injection wellfield figure.
    """

    (
        production,
        injection,
        width_ft,
        height_ft,
        area_sqft
    ) = create_open_loop_layout(
        number_of_installed_wells
    )

    fig_width, fig_height = get_figure_size(
        width_ft,
        height_ft
    )

    fig, ax = plt.subplots(
        figsize=(fig_width, fig_height)
    )

    marker_size = get_marker_size(
        number_of_installed_wells
    )

    # --------------------------------------------------------
    # Plot production wells
    # --------------------------------------------------------

    production_x = [
        x for x, y in production
    ]

    production_y = [
        y for x, y in production
    ]

    ax.scatter(
        production_x,
        production_y,
        s=marker_size,
        color="red",
        edgecolor="black",
        linewidth=0.6,
        zorder=3
    )

    # --------------------------------------------------------
    # Plot injection wells
    # --------------------------------------------------------

    injection_x = [
        x for x, y in injection
    ]

    injection_y = [
        y for x, y in injection
    ]

    ax.scatter(
        injection_x,
        injection_y,
        s=marker_size,
        color="blue",
        edgecolor="black",
        linewidth=0.6,
        zorder=3
    )

    # --------------------------------------------------------
    # Conceptual footprint
    # --------------------------------------------------------

    min_x = -PERIMETER_BUFFER_FT
    min_y = -PERIMETER_BUFFER_FT

    footprint = Rectangle(
        (
            min_x,
            min_y
        ),
        width_ft,
        height_ft,
        fill=False,
        edgecolor="gray",
        linewidth=1.5,
        linestyle="--",
        zorder=2
    )

    ax.add_patch(footprint)

    # --------------------------------------------------------
    # Plot margins
    # --------------------------------------------------------

    margin_x = max(
        width_ft * 0.05,
        100
    )

    margin_y = max(
        height_ft * 0.12,
        100
    )

    x_min_display = (
        min_x - margin_x
    )

    x_max_display = (
        min_x
        + width_ft
        + margin_x
    )

    y_min_display = (
        min_y - margin_y
    )

    y_max_display = (
        min_y
        + height_ft
        + margin_y
    )

    ax.set_xlim(
        x_min_display,
        x_max_display
    )

    ax.set_ylim(
        y_min_display,
        y_max_display
    )

    # --------------------------------------------------------
    # Scale bar
    # --------------------------------------------------------

    add_scale_bar(
        ax,
        width_ft,
        height_ft,
        x_min_display,
        y_min_display
    )

    # --------------------------------------------------------
    # Formatting
    # --------------------------------------------------------

    ax.set_aspect(
        "equal",
        adjustable="box"
    )

    ax.set_xlabel(
        "Distance (ft)",
        labelpad=8
    )

    ax.set_ylabel(
        "Distance (ft)",
        labelpad=8
    )

    ax.set_title(
        (
            f"{scenario_name}\n"
            f"{well_yield:,.0f} gpm per well | "
            f"{number_of_installed_wells} production + "
            f"{number_of_installed_wells} injection wells"
        ),
        pad=12
    )

    # --------------------------------------------------------
    # Legend
    # --------------------------------------------------------

    legend_marker_size = 8

    legend_elements = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="None",
            markerfacecolor="red",
            markeredgecolor="black",
            markersize=legend_marker_size,
            label="Production Wells"
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="None",
            markerfacecolor="blue",
            markeredgecolor="black",
            markersize=legend_marker_size,
            label="Injection Wells"
        ),
        Line2D(
            [0],
            [0],
            color="gray",
            linestyle="--",
            linewidth=1.5,
            label="Conceptual Footprint"
        )
    ]

    # Place legend outside the main plotting area so it does not
    # cover wells when the well count becomes larger.
    ax.legend(
        handles=legend_elements,
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
        borderaxespad=0
    )

    ax.grid(
        True,
        linestyle=":",
        linewidth=0.6,
        alpha=0.45
    )

    # Reserve room for the outside legend.
    fig.tight_layout(
        rect=[0, 0, 0.83, 1]
    )

    return (
        fig,
        width_ft,
        height_ft,
        area_sqft
    )


# ============================================================
# HEADER AND LOGO
# ============================================================

header_logo, header_title = st.columns(
    [1, 4],
    vertical_alignment="center"
)

with header_logo:

    if os.path.exists("egg_geo_logo.png"):
        st.image(
            "egg_geo_logo.png",
            width=220
        )

with header_title:

    st.title(
        "Open-Loop Geothermal Screening Tool"
    )


st.write(
    """
    This tool provides an early-stage estimate of the number of
    production and injection wells that may be required for an
    open-loop geothermal system based on estimated well yield and
    peak building load.

    The calculation assumes **2.5 gpm of groundwater flow per ton
    of peak load**. Actual system performance depends on site-specific
    hydrogeology, groundwater temperature, allowable temperature
    change, well construction, pumping conditions, and regulatory
    requirements.
    """
)


# ============================================================
# INPUTS
# ============================================================

st.header("Project Inputs")

st.info(
    "Adjust the numbers below and the screening results will "
    "automatically update."
)

col1, col2, col3 = st.columns(3)

with col1:

    minimum_well_yield = st.number_input(
        "Minimum Estimated Well Yield (gpm)",
        min_value=1.0,
        value=250.0,
        step=25.0,
        help=(
            "Conservative estimate of sustainable yield from one "
            "production or injection well."
        )
    )

with col2:

    maximum_well_yield = st.number_input(
        "Maximum Estimated Well Yield (gpm)",
        min_value=1.0,
        value=500.0,
        step=25.0,
        help=(
            "Higher estimate of sustainable yield from one "
            "production or injection well."
        )
    )

with col3:

    peak_load_tons = st.number_input(
        "Peak Load (tons)",
        min_value=1.0,
        value=500.0,
        step=25.0,
        help=(
            "Peak heating or cooling load that the open-loop "
            "wellfield is intended to serve."
        )
    )


# ============================================================
# INPUT VALIDATION
# ============================================================

if minimum_well_yield > maximum_well_yield:

    st.error(
        "Minimum estimated well yield must be less than or equal "
        "to maximum estimated well yield."
    )

    st.stop()


# ============================================================
# CALCULATIONS
# ============================================================

# Minimum yield = conservative case = more operating wells required
max_required_wells, total_required_flow_gpm = (
    calculate_required_well_count(
        peak_load_tons,
        minimum_well_yield
    )
)

# Maximum yield = optimistic case = fewer operating wells required
min_required_wells, _ = (
    calculate_required_well_count(
        peak_load_tons,
        maximum_well_yield
    )
)

# Add one redundant well of each type to both scenarios.
max_installed_wells = (
    max_required_wells
    + REDUNDANT_WELLS_PER_TYPE
)

min_installed_wells = (
    min_required_wells
    + REDUNDANT_WELLS_PER_TYPE
)

estimated_cost = (
    peak_load_tons
    * COST_PER_TON
)


# ============================================================
# RESULTS
# ============================================================

st.divider()

st.header("Screening Results")

st.write(
    f"""
    A peak load of **{peak_load_tons:,.0f} tons** corresponds to a
    **Total Required Flow of approximately
    {total_required_flow_gpm:,.0f} gpm** using the screening assumption
    of 2.5 gpm per ton.

    The well counts shown below include **one redundant production well
    and one redundant injection well** in each scenario.
    """
)


# ------------------------------------------------------------
# MAIN METRICS
# ------------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "Total Required Flow",
        f"{total_required_flow_gpm:,.0f} gpm"
    )

with col2:

    st.metric(
        "Production Wells",
        f"{min_installed_wells} – {max_installed_wells}"
    )

with col3:

    st.metric(
        "Injection Wells",
        f"{min_installed_wells} – {max_installed_wells}"
    )

with col4:

    st.metric(
        "Estimated Wellfield Cost",
        f"${estimated_cost:,.0f}"
    )


# ============================================================
# WELL YIELD SCENARIOS
# ============================================================

st.subheader(
    "Estimated Well Requirements"
)

scenario_col1, scenario_col2 = st.columns(2)


with scenario_col1:

    st.markdown(
        "### Minimum Well Yield Scenario"
    )

    st.write(
        f"""
        **Estimated well yield:**  
        {minimum_well_yield:,.0f} gpm/well

        **Required production wells:**  
        {max_required_wells}

        **Redundant production wells:**  
        {REDUNDANT_WELLS_PER_TYPE}

        **Total production wells:**  
        {max_installed_wells}

        **Required injection wells:**  
        {max_required_wells}

        **Redundant injection wells:**  
        {REDUNDANT_WELLS_PER_TYPE}

        **Total injection wells:**  
        {max_installed_wells}

        **Total installed wells:**  
        {max_installed_wells * 2}
        """
    )


with scenario_col2:

    st.markdown(
        "### Maximum Well Yield Scenario"
    )

    st.write(
        f"""
        **Estimated well yield:**  
        {maximum_well_yield:,.0f} gpm/well

        **Required production wells:**  
        {min_required_wells}

        **Redundant production wells:**  
        {REDUNDANT_WELLS_PER_TYPE}

        **Total production wells:**  
        {min_installed_wells}

        **Required injection wells:**  
        {min_required_wells}

        **Redundant injection wells:**  
        {REDUNDANT_WELLS_PER_TYPE}

        **Total injection wells:**  
        {min_installed_wells}

        **Total installed wells:**  
        {min_installed_wells * 2}
        """
    )


# ============================================================
# WELLFIELD LAYOUTS
# ============================================================

st.divider()

st.header(
    "Conceptual Wellfield Layout"
)

st.write(
    """
    The conceptual layouts below assume a minimum of **200 ft between
    wells of the same type** and **1,000 ft between the nearest
    production and injection wells**.

    Each scenario includes **one redundant production well and one
    redundant injection well**. An additional 100-ft perimeter is
    included around the outside of the conceptual wellfield when
    estimating its footprint.

    The figures are intended for early-stage site screening only.
    Actual well placement should consider site geometry, property
    boundaries, groundwater flow direction, hydrogeology, hydraulic
    interaction, thermal breakthrough, permitting requirements, and
    other site-specific constraints.
    """
)


# ------------------------------------------------------------
# MINIMUM YIELD SCENARIO
# ------------------------------------------------------------

st.subheader(
    "Minimum Well Yield Scenario"
)

fig_min, min_width, min_height, min_area = (
    create_wellfield_figure(
        max_installed_wells,
        max_required_wells,
        minimum_well_yield,
        "Minimum Well Yield Scenario"
    )
)

st.pyplot(
    fig_min,
    use_container_width=True
)

plt.close(fig_min)

min_area_acres = (
    min_area / 43560
)

min_col1, min_col2, min_col3 = st.columns(3)

with min_col1:

    st.metric(
        "Conceptual Footprint",
        f"{min_area:,.0f} sq ft"
    )

with min_col2:

    st.metric(
        "Approximate Area",
        f"{min_area_acres:,.2f} acres"
    )

with min_col3:

    st.metric(
        "Approximate Dimensions",
        f"{min_width:,.0f} × {min_height:,.0f} ft"
    )


# ------------------------------------------------------------
# MAXIMUM YIELD SCENARIO
# ------------------------------------------------------------

st.subheader(
    "Maximum Well Yield Scenario"
)

fig_max, max_width, max_height, max_area = (
    create_wellfield_figure(
        min_installed_wells,
        min_required_wells,
        maximum_well_yield,
        "Maximum Well Yield Scenario"
    )
)

st.pyplot(
    fig_max,
    use_container_width=True
)

plt.close(fig_max)

max_area_acres = (
    max_area / 43560
)

max_col1, max_col2, max_col3 = st.columns(3)

with max_col1:

    st.metric(
        "Conceptual Footprint",
        f"{max_area:,.0f} sq ft"
    )

with max_col2:

    st.metric(
        "Approximate Area",
        f"{max_area_acres:,.2f} acres"
    )

with max_col3:

    st.metric(
        "Approximate Dimensions",
        f"{max_width:,.0f} × {max_height:,.0f} ft"
    )


# ============================================================
# COST ESTIMATE
# ============================================================

st.divider()

st.header(
    "Conceptual Cost Estimate"
)

st.metric(
    "Estimated Open-Loop Wellfield Cost",
    f"${estimated_cost:,.0f}"
)

st.write(
    f"""
    The conceptual wellfield cost is estimated using a generalized
    screening value of **${COST_PER_TON:,.0f} per ton** of peak system
    capacity. For a peak load of **{peak_load_tons:,.0f} tons**, this
    produces an estimated wellfield cost of approximately
    **${estimated_cost:,.0f}**.

    Open-loop geothermal wellfield costs are highly site dependent and
    can vary considerably from this screening estimate. Important cost
    variables include drilling depth, local geology, aquifer conditions,
    required well diameter and construction, local demand for drilling
    contractors, drilling-rig mobilization and transportation, site
    accessibility, urban or constrained working conditions, remote or
    mountainous locations, permitting, pump testing, injection testing,
    groundwater treatment requirements, and other site-specific
    conditions.

    This estimate should therefore be used for **early-stage feasibility
    screening only** and should not be considered a contractor quote or
    project-level cost estimate.
    """
)


# ============================================================
# DESIGN ASSUMPTIONS
# ============================================================

with st.expander(
    "Screening Assumptions"
):

    st.markdown(
        f"""
        - Groundwater demand: **{GPM_PER_TON} gpm per ton**
        - Minimum like-well spacing: **{LIKE_WELL_SPACING_FT:,} ft**
        - Minimum production-to-injection separation:
          **{PRODUCTION_INJECTION_SEPARATION_FT:,} ft**
        - Conceptual perimeter allowance:
          **{PERIMETER_BUFFER_FT:,.0f} ft**
        - One redundant production well is included in each scenario.
        - One redundant injection well is included in each scenario.
        - Screening-level wellfield cost:
          **${COST_PER_TON:,.0f} per ton**
        - Production and injection well counts are assumed to be equal.
        - Each operating well is assumed to provide its entered
          sustainable yield.
        - Redundant wells are not counted toward required operating flow.
        - Pumping energy is not estimated.
        - Building-side geothermal equipment is not included in the
          cost estimate.
        - Actual wellfield feasibility requires site-specific
          hydrogeologic investigation and testing.
        """
    )