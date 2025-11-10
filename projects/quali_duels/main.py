from qualifying_duel_builder import QualifyingDuelBuilder

if __name__ == "__main__":
    builder = QualifyingDuelBuilder(season=2025)
    builder.fetch_duels_for_all_rounds()
    builder.export_csv()
