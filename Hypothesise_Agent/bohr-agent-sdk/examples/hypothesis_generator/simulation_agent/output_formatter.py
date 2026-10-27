"""
Output Formatter
Normalizes engine outputs to SimulationOutput schema
"""

from .schema import SimulationOutput, PlotData, SeriesData


def format_output(raw: dict, procedure: dict) -> SimulationOutput:
    """
    Takes raw engine output dict and wraps it into the
    typed SimulationOutput schema for downstream consumers.
    """
    plots = []
    for p in raw.get("plot_data", []):
        try:
            # Support both numeric and string x labels
            raw_x = p.get("x", [])
            try:
                x_vals = [float(v) for v in raw_x]
            except (ValueError, TypeError):
                x_vals = list(raw_x)

            raw_y = p.get("y", [])
            try:
                y_vals = [float(v) for v in raw_y]
            except (ValueError, TypeError):
                y_vals = list(raw_y)

            # Parse extra series for multi-line plots
            extra_series = None
            raw_extra = p.get("extra_series", [])
            if raw_extra:
                extra_series = []
                for s in raw_extra:
                    try:
                        sy = [float(v) for v in s.get("y", [])]
                    except (ValueError, TypeError):
                        sy = list(s.get("y", []))
                    extra_series.append(SeriesData(
                        y=sy,
                        name=s.get("name", "Series"),
                        color=s.get("color"),
                    ))

            plots.append(PlotData(
                plot_type=p.get("plot_type", "line"),
                title=p.get("title", "Simulation Result"),
                x_label=p.get("x_label", "X"),
                y_label=p.get("y_label", "Y"),
                x=x_vals,
                y=y_vals,
                series_name=p.get("series_name"),
                extra_series=extra_series,
            ))
        except Exception as e:
            print(f"⚠️  Skipping invalid plot data: {e}")
            continue

    return SimulationOutput(
        status=raw.get("status", "success" if "error" not in raw else "fallback"),
        engine_used=raw.get("engine_used", "unknown"),
        domain=procedure.get("domain", "general"),
        hypothesis=procedure.get("hypothesis", ""),
        numerical_results=raw.get("numerical_results", {}),
        plot_data=plots,
        observations=raw.get("observations", []),
        confidence_score=float(raw.get("confidence_score", 0.5)),
        simulation_log=raw.get("simulation_log", []),
        visualization_type=raw.get("visualization_type", "graph"),
        visual_data=raw.get("visual_data", None),
    )
