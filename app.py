import math
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

# Adds half of the 200-ft well spacing around the outside
# of the conceptual wellfield.
PERIMETER_BUFFER_FT = LIKE_WELL_SPACING_FT / 2

COST_PER_TON = 12500


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def calculate_well_count(peak_load_tons, well_yield_gpm):
    """
    Calculate the number of production wells and injection wells
    needed to meet the required flow.

    Assumes:
        2.5 gpm = 1 ton
        Production and injection well counts are equal.
    """

    required_flow_gpm = peak_load_tons * GPM_PER_TON

    if well_yield_gpm <= 0:
        return 0, required_flow_gpm

    number_of_wells = math.ceil(required_flow_gpm / well_yield_gpm)

    return number_of_wells, required_flow_gpm


def make_grid_coordinates(number_of_wells, spacing):
    """
    Create a compact, roughly square grid for one group of wells.
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


def create_open_loop_layout(number_of_wells):
    """
    Create production and injection well coordinates.

    Production wells are placed in one compact grid.
    Injection wells are placed to the right.

    The closest production and injection wells are separated
    by at least 1,000 ft.

    A 100-ft perimeter buffer is then added around the entire
    conceptual wellfield for area calculations.
    """

    production = make_grid_coordinates(
        number_of_wells,
        LIKE_WELL_SPACING_FT
    )

    injection_local = make_grid_coordinates(
        number_of_wells,
        LIKE_WELL_SPACING_FT
    )

    if not production:
        return [], [], 0, 0, 0

    # Maximum X coordinate of production well group
    production_max_x = max(x for x, y in production)

    # Move injection field so the closest injection well is
    # exactly 1,000 ft from the closest production well.
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

    # Add perimeter buffer around all outside edges
    field_width_ft = (
        max_x - min_x
        + 2 * PERIMETER_BUFFER_FT
    )

    field_height_ft = (
        max_y - min_y
        + 2 * PERIMETER_BUFFER_FT
    )

    field_area_sqft = field_width_ft * field_height_ft

    return (
        production,
        injection,
        field_width_ft,
        field_height_ft,
        field_area_sqft
    )


def add_scale_bar(ax, field_width, field_height):
    """
    Add a simple graphical scale bar to the plot.
    """

    if field_width >= 2500:
        scale_length = 500
    elif field_width >= 1200:
        scale_length = 200
    else:
        scale_length = 100

    x_start = -PERIMETER_BUFFER_FT + field_width * 0.05
    y_start = -PERIMETER_BUFFER_FT + field_height * 0.06

    ax.plot(
        [x_start, x_start + scale_length],
        [y_start, y_start],
        color="black",
        linewidth=3
    )

    ax.plot(
        [x_start, x_start],
        [y_start - 15, y_start + 15],
        color="black",
        linewidth=2
    )

    ax.plot(
        [x_start + scale_length, x_start + scale_length],
        [y_start - 15, y_start + 15],
        color="black",
        linewidth=2
    )

    ax.text(
        x_start + scale_length / 2,
        y_start + 25,
        f"{scale_length:,} ft",
        ha="center",
        va="bottom",
        fontsize=9
    )


def create_wellfield_figure(
    number_of_wells,
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
    ) = create_open_loop_layout(number_of_wells)

    fig, ax = plt.subplots(figsize=(10, 6))

    # --------------------------------------------------------
    # Plot wells
    # --------------------------------------------------------

    production_x = [x for x, y in production]
    production_y = [y for x, y in production]

    injection_x = [x for x, y in injection]
    injection_y = [y for x, y in injection]

    ax.scatter(
        production_x,
        production_y,
        s=90,
        color="red",
        edgecolor="black",
        linewidth=0.6,
        zorder=3,
        label="Production Wells"
    )

    ax.scatter(
        injection_x,
        injection_y,
        s=90,
        color="blue",
        edgecolor="black",
        linewidth=0.6,
        zorder=3,
        label="Injection Wells"
    )

    # --------------------------------------------------------
    # Conceptual footprint
    # --------------------------------------------------------

    footprint = Rectangle(
        (-PERIMETER_BUFFER_FT, -PERIMETER_BUFFER_FT),
        width_ft,
        height_ft,
        fill=False,
        edgecolor="gray",
        linewidth=1.5,
        linestyle="--"
    )

    ax.add_patch(footprint)

    # --------------------------------------------------------
    # Scale bar
    # --------------------------------------------------------

    add_scale_bar(
        ax,
        width_ft,
        height_ft
    )

    # --------------------------------------------------------
    # Formatting
    # --------------------------------------------------------

    ax.set_aspect("equal", adjustable="box")

    ax.set_xlabel("Distance (ft)")
    ax.set_ylabel("Distance (ft)")

    ax.set_title(
        f"{scenario_name}\n"
        f"{well_yield:,.0f} gpm per well | "
        f"{number_of_wells} production + "
        f"{number_of_wells} injection wells"
    )

    # Provide enough room around the footprint
    margin_x = max(width_ft * 0.05, 75)
    margin_y = max(height_ft * 0.12, 75)

    ax.set_xlim(
        -PERIMETER_BUFFER_FT - margin_x,
        -PERIMETER_BUFFER_FT + width_ft + margin_x
    )

    ax.set_ylim(
        -PERIMETER_BUFFER_FT - margin_y,
        -PERIMETER_BUFFER_FT + height_ft + margin_y
    )

    # Custom legend
    legend_elements = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="red",
            markeredgecolor="black",
            markersize=9,
            label="Production Wells"
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="blue",
            markeredgecolor="black",
            markersize=9,
            label="Injection Wells"
        )
    ]

    ax.legend(
        handles=legend_elements,
        loc="upper right"
    )

    ax.grid(
        True,
        linestyle=":",
        linewidth=0.6,
        alpha=0.5
    )

    # Area annotation
    area_acres = area_sqft / 43560

    ax.text(
        0.5,
        -0.14,
        (
            f"Conceptual Wellfield Footprint: "
            f"{area_sqft:,.0f} sq ft "
            f"({area_acres:,.2f} acres)"
        ),
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=10
    )

    plt.tight_layout()

    return fig, width_ft, height_ft, area_sqft


# ============================================================
# APP HEADER
# ============================================================

st.title("Open-Loop Geothermal Screening Tool")

st.write(
    """
    This screening tool provides an early estimate of the number of
    production and injection wells required for an open-loop geothermal
    system based on estimated well yield and peak building load.

    The calculation assumes **2.5 gpm of groundwater flow per ton of
    peak load**. Actual open-loop system performance depends strongly on
    site-specific hydrogeology, groundwater temperature, allowable
    temperature change, well construction, pumping conditions, and
    regulatory requirements.
    """
)


# ============================================================
# INPUTS
# ============================================================

st.header("Project Inputs")

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

maximum_well_count, required_flow_gpm = calculate_well_count(
    peak_load_tons,
    minimum_well_yield
)

minimum_well_count, _ = calculate_well_count(
    peak_load_tons,
    maximum_well_yield
)


estimated_cost = peak_load_tons * COST_PER_TON


# ============================================================
# RESULTS
# ============================================================

st.divider()

st.header("Screening Results")

st.write(
    f"""
    A peak load of **{peak_load_tons:,.0f} tons** corresponds to an
    estimated design groundwater flow of approximately
    **{required_flow_gpm:,.0f} gpm** using the screening assumption of
    2.5 gpm per ton.
    """
)


# ------------------------------------------------------------
# MAIN METRICS
# ------------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "Required Flow",
        f"{required_flow_gpm:,.0f} gpm"
    )


with col2:

    st.metric(
        "Production Wells",
        f"{minimum_well_count} – {maximum_well_count}"
    )


with col3:

    st.metric(
        "Injection Wells",
        f"{minimum_well_count} – {maximum_well_count}"
    )


with col4:

    st.metric(
        "Estimated Wellfield Cost",
        f"${estimated_cost:,.0f}"
    )


# ============================================================
# WELL YIELD SCENARIOS
# ============================================================

st.subheader("Estimated Well Requirements")

scenario_col1, scenario_col2 = st.columns(2)


with scenario_col1:

    st.markdown("### Minimum Yield Scenario")

    st.write(
        f"""
        **Estimated well yield:** {minimum_well_yield:,.0f} gpm/well

        **Production wells:** {maximum_well_count}

        **Injection wells:** {maximum_well_count}

        **Total wells:** {maximum_well_count * 2}
        """
    )


with scenario_col2:

    st.markdown("### Maximum Yield Scenario")

    st.write(
        f"""
        **Estimated well yield:** {maximum_well_yield:,.0f} gpm/well

        **Production wells:** {minimum_well_count}

        **Injection wells:** {minimum_well_count}

        **Total wells:** {minimum_well_count * 2}
        """
    )


# ============================================================
# WELLFIELD LAYOUTS
# ============================================================

st.divider()

st.header("Conceptual Wellfield Layout")

st.write(
    """
    The conceptual layouts below assume a minimum of **200 ft between
    wells of the same type** and **1,000 ft between production and
    injection wells**. An additional 100-ft perimeter is included around
    the outside of the wellfield when estimating the required footprint.

    These layouts are intended for early-stage site screening only.
    Actual well placement should be based on site geometry, hydrogeologic
    conditions, groundwater flow direction, property boundaries,
    permitting requirements, and evaluation of potential thermal or
    hydraulic interaction between wells.
    """
)


# ------------------------------------------------------------
# MINIMUM YIELD / MAXIMUM WELL COUNT FIGURE
# ------------------------------------------------------------

st.subheader("Minimum Well Yield Scenario")

fig_min, min_width, min_height, min_area = create_wellfield_figure(
    maximum_well_count,
    minimum_well_yield,
    "Minimum Well Yield Scenario"
)

st.pyplot(fig_min)

plt.close(fig_min)

min_area_acres = min_area / 43560


min_col1, min_col2, min_col3 = st.columns(3)

with min_col1:

    st.metric(
        "Total Area",
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
# MAXIMUM YIELD / MINIMUM WELL COUNT FIGURE
# ------------------------------------------------------------

st.subheader("Maximum Well Yield Scenario")

fig_max, max_width, max_height, max_area = create_wellfield_figure(
    minimum_well_count,
    maximum_well_yield,
    "Maximum Well Yield Scenario"
)

st.pyplot(fig_max)

plt.close(fig_max)

max_area_acres = max_area / 43560


max_col1, max_col2, max_col3 = st.columns(3)

with max_col1:

    st.metric(
        "Total Area",
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

st.header("Conceptual Cost Estimate")

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

with st.expander("Screening Assumptions"):

    st.markdown(
        f"""
        - Groundwater demand: **{GPM_PER_TON} gpm per ton**
        - Minimum like-well spacing: **{LIKE_WELL_SPACING_FT:,} ft**
        - Minimum production-to-injection separation:
          **{PRODUCTION_INJECTION_SEPARATION_FT:,} ft**
        - Conceptual perimeter allowance: **{PERIMETER_BUFFER_FT:,.0f} ft**
        - Screening-level wellfield cost:
          **${COST_PER_TON:,.0f} per ton**
        - Production and injection well counts are assumed to be equal.
        - Each well is assumed to provide its entered sustainable yield.
        - Well redundancy or standby wells are not included.
        - Pumping energy is not estimated.
        - Building-side geothermal equipment is not included in the
          cost estimate.
        - Actual wellfield feasibility requires site-specific
          hydrogeologic investigation and testing.
        """
    )