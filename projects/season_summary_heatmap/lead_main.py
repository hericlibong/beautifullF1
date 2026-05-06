from exporter_lead import F1FlourishExporterLead


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(description="Export F1 season leaders heatmap CSV.")
    parser.add_argument("--season", type=int, default=2025, help="Season to export.")
    parser.add_argument(
        "--output",
        default=None,
        help="CSV filename in outputs/ or an absolute output path.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    exporter = F1FlourishExporterLead(season=args.season, output_csv=args.output)
    exporter.fetch_results()
    exporter.build_dataframe()
    exporter.patch_headshots()
    exporter.finalize_dataframe()
    exporter.export()
