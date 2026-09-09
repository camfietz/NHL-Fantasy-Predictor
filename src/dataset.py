import argparse
import csv
import os
import pprint
import re

POINT_VALUES = {
    "goals": 2.0,
    "assists": 1.0,
    "shots": 0.0,
    "blocks": 0.25,
    "hits": 0.1,
    "powerplay_goals": 1.0,
    "shorthanded_goals": 1.0,
}

class Player:
    def __init__(self, id='0000000', season='0000', name='NAME', team='TEAM', position='POS', games_played='0', goals='0', assists='0', powerplay_goals='0', shorthanded_goals='0', special_goals='0', expected_goals = '0', shots='0', hits='0', blocks='0', fantasy_score='0'):
        self.id = int(id)
        self.season = int(season)
        self.name = str(name)
        self.team = str(team)
        self.position = str(position)
        self.games_played = float(games_played)
        self.goals = float(goals)
        self.assists = float(assists)
        self.powerplay_goals = float(powerplay_goals)
        self.shorthanded_goals = float(shorthanded_goals)
        self.special_goals = float(special_goals)
        self.expected_goals = float(expected_goals)
        self.shots = float(shots)
        self.hits = float(hits)
        self.blocks = float(blocks)
        self.fantasy_score = float(fantasy_score)

    def get_fantasy_score(self):
        fs = (
            POINT_VALUES["goals"] * self.goals
            + POINT_VALUES["assists"] * self.assists
            + POINT_VALUES["shots"] * self.shots
            + POINT_VALUES["blocks"] * self.blocks
            + POINT_VALUES["hits"] * self.hits
            + POINT_VALUES["powerplay_goals"] * self.powerplay_goals
            + POINT_VALUES["shorthanded_goals"] * self.shorthanded_goals
        )
        return fs

    def __str__(self):
        return str(self.name) + " " + str(self.position) + " " + str(self.season) + '-' + str(self.season + 1)[-2:] + " " + str(self.games_played) + "GP " + str(round(self.goals)) + "G " + str(round(self.assists)) + "A " + str(round(round(self.goals))+ round(self.assists)) + "P " + str(round(self.powerplay_goals)) + "PPG " + str(round(self.shorthanded_goals)) + "SHG " + str(round(self.shots)) + "SOG " + str(round(self.hits)) + "H " + str(round(self.blocks)) + "B " + str(round(self.fantasy_score,1)) + "FS"

    __repr__ = __str__

    def __iter__(self):
        return self
    
dataset_dictionary = {}

# Load every season file present in the data directory.
current_dir = os.path.dirname(__file__)
data_dir = os.path.join(current_dir, '../data/moneypuck')
season_files = []
for filename in os.listdir(data_dir):
    match = re.fullmatch(r'moneypuck_(\d{4})-(\d{2})\.csv', filename)
    if match:
        season_files.append((int(match.group(1)), os.path.join(data_dir, filename)))

for season, file_path in sorted(season_files):
    season_dictionary = {}
 
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        headers = next(reader)
        for row in reader:
            # create dictionary entry
            id = int(row[0])
            if id not in season_dictionary:
                season_dictionary[id] = Player(id=id)

            # all situations
            if (row[5] == 'all'):
                season_dictionary[id].season = int(row[1])
                season_dictionary[id].name = str(row[2])
                season_dictionary[id].team = str(row[3])
                if str(row[4]) == 'L' or str(row[4]) == 'R':
                    season_dictionary[id].position = 'W'
                else:
                    season_dictionary[id].position = str(row[4])
                season_dictionary[id].games_played = float(row[6])
                season_dictionary[id].goals = float(row[34])
                season_dictionary[id].assists = float(row[27])+float(row[28])
                season_dictionary[id].points = float(row[33])
                season_dictionary[id].expected_goals = float(row[18])
                season_dictionary[id].shots = float(row[29])
                season_dictionary[id].hits = float(row[46])
                season_dictionary[id].blocks = float(row[83])

            # powerplay (5on4 only)
            elif (row[5] == '5on4'):
                season_dictionary[id].powerplay_goals = float(row[34])

            # shorthanded (4on5 only)
            elif (row[5] == '4on5'):
                season_dictionary[id].shorthanded_goals = float(row[34])

            # all other situations (5on3, 6on5, 3on3, etc.)
            elif (row[5] == 'other'):
                season_dictionary[id].special_goals = float(row[34])

        dataset_dictionary[season] = season_dictionary
        #pprint.pprint(season_dictionary)

def search_players(name):
    """Find unique player IDs whose names contain the supplied text."""
    LUT_id = []
    keys = list(dataset_dictionary.keys())
    for season in range(keys[len(keys)-1], keys[0]-1, -1):
        for id in dataset_dictionary[season]:
            if name.lower() in dataset_dictionary[season][id].name.lower():
                entry = str(id)
                if entry not in LUT_id:
                    LUT_id.append(entry)
                    player = dataset_dictionary[season][id]
                    yield player.name, player.team, player.position, entry


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('name', help="name of player")
    args = parser.parse_args()
    for name, team, position, id in search_players(args.name):
        print(f"{name} {team} {position} [{id}]")
