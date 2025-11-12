from exporter import F1FlourishExporter

if __name__ == "__main__":
    exporter = F1FlourishExporter(season=2025, output_csv="f1_2025_full_heatmap.csv")
    exporter.fetch_results()
    exporter.build_dataframe()
    exporter.patch_headshots()
    exporter.finalize_dataframe()
    exporter.export()
