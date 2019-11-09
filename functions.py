import json
import os
import requests
from os import path

def load_card_data():
    '''Sets up card dictionary'''
    cards = {}
    card_data = read_card_data()
    for card in card_data:
        card_name = card['name'].split(' //')[0]
        cards[card_name] = card
    return cards

def read_card_data():
    '''Loads card data from cache or Scryfall'''
    if path.exists('card-data.json'):
        with open('card-data.json') as json_file:
            data = json.load(json_file)
            resp = requests.head('https://archive.scryfall.com/json/scryfall-default-cards.json')
            if resp.headers['etag'] == data['etag']:
                print('Cached data valid')
                return data['data']
    return refresh_card_data()

def refresh_card_data():
    '''Fetches card data from Scryfall and saves it to disk'''
    print('Fetching card data...')
    resp = requests.get('https://archive.scryfall.com/json/scryfall-default-cards.json')
    cache_data = {}
    cache_data['etag'] = resp.headers['etag']
    cache_data['data'] = resp.json()
    with open('card-data.json', 'w') as outfile:
        json.dump(cache_data, outfile)
    return cache_data['data']

def read_decklists(directory):
    '''Loads all decklists in a given directory'''
    decks = {}
    for infile in os.listdir(directory):
        if infile[-4:] != '.txt':
            continue
        filename = directory + '/' + infile
        try:
            deck = load_deck(filename)
            deck_id = deck['deck_id']
            decks[deck_id] = deck

        except:
            print('File {} could not be analyzed.'.format(filename))
            continue
    return decks

def load_deck(infile):
    '''Loads a single decklist'''
    with open(infile) as deck_file:
        lines = [line.strip('\n') for line in deck_file.readlines()]
        num_lines = len(lines)
        deck_id = lines[0].split(':')[1].strip(' ')
        player_id = lines[1].split(':')[1].strip(' ')
        date = lines[2].split(':')[1].strip(' ')
        colors = lines[3].split(':')[1].strip(' ')
        labels = lines[4].split(':')[1].strip(' ').split(',')
        match_record = lines[5].split(':')[1].strip(' ').split('-')
        match_wins = match_record[0]
        match_losses = match_record[1]
        match_draws = 0
        if len(match_record) == 3:
            match_draws = match_record[2]
        game_record = lines[6].split(':')[1].strip(' ').split('-')
        game_wins = game_record[0]
        game_losses = game_record[1]
        game_draws = 0
        if len(game_record) == 3:
            game_draws = game_record[2]
        index = 7
        games = {}
        while lines[index] != '':
            game_data = lines[index].split(':')
            opponent = game_data[0].split('.')[1].strip(' ')
            record = game_data[1].strip(' ').split('-')
            wins = record[0]
            losses = record[1]
            draws = 0
            if len(record) == 3:
                draws = record[2]
            games[opponent] = {'wins': wins, 'losses': losses, 'draws': draws}
            index += 1
        index += 1
        maindeck = []
        sideboard = []

        while index < num_lines and lines[index] != '':
            num, card_name = lines[index].split(' ', 1)
            maindeck.extend([card_name]*int(num))
            index += 1
        index += 1
        while index < num_lines and lines[index] != '':
            num, card_name = lines[index].split(' ', 1)
            sideboard.extend([card_name]*int(num))
            index += 1
        
        deck = {
            'deck_id': deck_id,
            'player_id': player_id,
            'date': date,
            'colors': colors,
            'labels': labels,
            'match_record': {'wins': match_wins, 'losses': match_losses, 'draws': match_draws},
            'game_record': {'wins': game_wins, 'losses': game_losses, 'draws': game_draws},
            'game_results': games,
            'maindeck': maindeck,
            'sideboard': sideboard}
        return deck

def validate_decklists(decks, cards):
    for deck in decks.values():
        deck_id = deck['deck_id']
        if len(deck['maindeck']) < 40:
            print('maindeck for deck {} missing cards'.format(deck_id))
        for card in deck['maindeck'] + deck['sideboard']:
            if card not in cards.keys():
                print('misspelled or missing card: {}'.format(card))
        for opponent in deck['game_results'].keys():
            if opponent not in decks:
                print('missing deck_id: {}'.format(opponent))

def main():
    card_data = load_card_data()
    decks = read_decklists('draft-results')
    validate_decklists(decks, card_data)

if __name__ == '__main__':
    main()
