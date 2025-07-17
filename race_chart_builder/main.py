from race_chart_builder import F1RaceChartBuilder

if __name__ == "__main__":
    builder = F1RaceChartBuilder(season=2025, rounds=12, meeting_key=1255)
    builder.fetch_driver_images()
    builder.fetch_sprint_results()
    builder.build_results_table()
    builder.export_csv()
