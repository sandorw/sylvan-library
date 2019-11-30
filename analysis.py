import argparse
import collections
import json
import os
import pprint
import requests
from os import path

def load_card_data(is_offline):
    '''Sets up card dictionary'''
    cards = {}
    card_data = read_card_data(is_offline)
    if not card_data:
        raise RuntimeError('No card data available')
    for card in card_data:
        card_name = card['name'].split(' //')[0]
        cards[card_name] = card
    return cards

def read_card_data(is_offline):
    '''Loads card data from cache or Scryfall'''
    if path.exists('card-data.json'):
        with open('card-data.json') as json_file:
            data = json.load(json_file)
            if is_offline:
                return data['data']
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

def read_decklists(dirs):
    '''Loads all decklists in a given directory'''
    decks = {}
    for dir in dirs:
        for infile in os.listdir(dir):
            if infile[-4:] != '.txt':
                continue
            filename = dir + '/' + infile
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
        labels = lines[4].split(':')[1].split(',')
        labels = [x.strip(' ') for x in labels]
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
            opponent = int(game_data[0].split('.')[1].strip(' '))
            record = game_data[1].strip(' ').split('-')
            wins = record[0]
            losses = record[1]
            draws = 0
            if len(record) == 3:
                draws = record[2]
            games[opponent] = {'wins': int(wins), 'losses': int(losses), 'draws': int(draws)}
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
            'deck_id': int(deck_id),
            'player_id': int(player_id),
            'date': date,
            'colors': colors,
            'labels': labels,
            'match_record': {'wins': int(match_wins), 'losses': int(match_losses), 'draws': int(match_draws)},
            'game_record': {'wins': int(game_wins), 'losses': int(game_losses), 'draws': int(game_draws)},
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
        for match_record in deck['game_results'].items():
            opponent = match_record[0]
            if opponent not in decks:
                print('missing deck_id: {}'.format(opponent))
                continue
            opposing_deck = decks[opponent]
            if deck_id not in opposing_deck['game_results'].keys():
                print('missing match record in deck_id {} against deck_id {}'.format(opponent, deck_id))
                continue
            record = match_record[1]
            expected = {'wins': record['losses'], 'losses': record['wins'], 'draws': record['draws']}
            if opposing_deck['game_results'][deck_id] != expected:
                print('wrong match result for deck_id {} against deck_id {}'.format(opponent, deck_id))

def analyze_winrate(card_data, decks, deck_predicate, params):
    win_rates = {}
    for deck in decks.values():
        if not deck_predicate(deck):
            continue
        analyze_winrate_recursive(decks, deck, params, win_rates, deck['game_record'])
    calculate_winrate_recursive(win_rates)
    pprint.pprint(win_rates)

def analyze_winrate_recursive(decks, deck, params, record, game_record):
    if not params:
        if not record:
            record['wins'] = 0
            record['losses'] = 0
            record['draws'] = 0
        accumulate_results(record, game_record)
        return
    next_param = params[0]
    opposing_prefix = "opposing_"
    if next_param.startswith(opposing_prefix):
        stripped_param = next_param[len(opposing_prefix):]
        for match_result in deck['game_results'].items():
            opposing_deck_id = match_result[0]
            match_record = match_result[1]
            groupings = extract_groupings(decks[opposing_deck_id], stripped_param)
            for grouping in groupings:
                if grouping not in record.keys():
                    record[grouping] = {}
                analyze_winrate_recursive(decks, deck, params[1:], record[grouping], match_record)
    else:
        groupings = extract_groupings(deck, next_param)
        for grouping in groupings:
            if grouping not in record.keys():
                record[grouping] = {}
            analyze_winrate_recursive(decks, deck, params[1:], record[grouping], game_record)

def accumulate_results(record, results):
    record['wins'] += results['wins']
    record['losses'] += results['losses']
    record['draws'] += results['draws']

def calculate_winrate_recursive(record):
    if 'wins' in record.keys():
        record['winrate'] = get_winrate(record)
    else:
        for value in record.values():
            calculate_winrate_recursive(value)

def get_winrate(record):
    return float(record['wins']) / (record['wins'] + record['losses'] + record['draws'])

def analyze_counts(card_data, decks, deck_predicate, params):
    counts = {}
    for deck in decks.values():
        if not deck_predicate(deck):
            continue
        analyze_counts_recursive(decks, deck, params, counts)
    calculate_counts_recursive(counts)
    pprint.pprint(counts)

def analyze_counts_recursive(decks, deck, params, counts):
    if not params:
        raise RuntimeError('Missing grouping param')
    next_param = params[0]
    opposing_prefix = "opposing_"
    if next_param.startswith(opposing_prefix):
        stripped_param = next_param[len(opposing_prefix):]
        for opposing_deck_id in deck['game_results'].keys():
            groupings = extract_groupings(decks[opposing_deck_id], stripped_param)
            analyze_counts_recursive_inner(decks, deck, params, counts, groupings)
    else:
        groupings = extract_groupings(deck, params[0])
        analyze_counts_recursive_inner(decks, deck, params, counts, groupings)

def analyze_counts_recursive_inner(decks, deck, params, counts, groupings):
    for grouping in groupings:
        if len(params) == 1:
            if grouping not in counts.keys():
                counts[grouping] = 0
            counts[grouping] += 1
        else:
            if grouping not in counts.keys():
                counts[grouping] = {}
            if len(params) == 2:
                if 'count' not in counts[grouping].keys():
                    counts[grouping]['count'] = 0
                counts[grouping]['count'] += 1
            analyze_counts_recursive(decks, deck, params[1:], counts[grouping])

def extract_groupings(deck, param):
    grouping = deck[param]
    if isinstance(grouping, collections.Mapping):
        raise RuntimeError('Invalid grouping parameter')
    elif isinstance(grouping, list):
        return grouping
    else:
        return [grouping]

def calculate_counts_recursive(counts):
    value = list(counts.values())[0]
    if isinstance(value, collections.Mapping):
        for dict_value in counts.values():
            calculate_counts_recursive(dict_value)
    elif 'count' in counts.keys():
        count = counts['count']
        for key in counts.keys():
            if key == 'count':
                continue
            value = counts[key]
            fraction = float(value) / count
            counts[key] = {'count': value, 'fraction': fraction}

def main():
    parser = argparse.ArgumentParser(description='Analyzes cube decklists')
    parser.add_argument('--offline', action='store_true', help='Use local cached card data')
    parser.add_argument('-d', '--dir', nargs='+', help='Directory to read draft results from')
    parser.add_argument('-p', '--player', nargs='+', help='Filter results to decks played by a certain player ID')
    parser.add_argument('-a', '--archetype', nargs='+', help='Filter results to decks of a certain archetype')
    parser.add_argument('--winrate', nargs='*', help='Calculate winrate grouped by the arguments in order')
    parser.add_argument('--count', nargs='*', help='Calculate counts and fractions groups by the arguments in order')
    args = parser.parse_args()

    deck_predicate = lambda deck: (not args.player or deck['player_id'] in map(int, args.player)) and (not args.archetype or (set(args.archetype) & set(deck['labels'])))

    card_data = {}
    card_data = load_card_data(args.offline)
    decks = read_decklists(args.dir)
    validate_decklists(decks, card_data)

    if args.winrate:
        analyze_winrate(card_data, decks, deck_predicate, args.winrate)
    if args.count:
        analyze_counts(card_data, decks, deck_predicate, args.count)

    # TODO
    # better formatting, include grouping name in outputs
    # maindeck rates support
    # filters based on card attributes, e.g. winrate/maindeck rate of planeswalkers, white cards, etc.

if __name__ == '__main__':
    main()
