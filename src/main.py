import argparse
import csv
import os
import pprint
import numpy as np

from dataset import dataset_dictionary
from predict_score import predict_player, predict_season

parser = argparse.ArgumentParser()
parser.add_argument('season', help="season to predict (xxxx-xx)")
parser.add_argument('id', help="player ID / 'all' / 'f' / 'd' ", type=lambda s: s.lower())
args = parser.parse_args()

season = int(args.season.split("-")[0])

# predict season or specific player
if args.id == 'all' or args.id == 'f' or args.id == 'd':
    ranking, mpd = predict_season(season, str(args.id))
    pprint.pprint(ranking)
    if mpd is not None:
        print('Accuracy = {:.1%}'.format(1-mpd))
else:
    ranking, pd = predict_player(season, int(args.id), 'all')
    pprint.pprint(ranking)
    if pd is not None:
        print('Accuracy = {:.1%}'.format(1-pd))
