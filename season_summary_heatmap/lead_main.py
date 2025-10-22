from exporter_lead import F1FlourishExporterLead

if __name__ == "__main__":
    exporter = F1FlourishExporterLead(season=2025, output_csv="f1_2025_flourish_leadership.csv")
    exporter.fetch_results()
    exporter.build_dataframe()
    exporter.patch_headshots()
    exporter.finalize_dataframe()
    exporter.export()
