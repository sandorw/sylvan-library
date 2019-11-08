import json
import os
import requests
from os import path

def load_card_data():
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
    

def main():
    card_data = load_card_data()
    

if __name__ == '__main__':
    main()
