import argparse
import readline
import random

def simulate(population, sample, threshold):
    samples = 100000
    successes = 0
    for _ in range(samples):
        random.shuffle(population)
        total=0
        for i in range(sample):
            total += population[i]
        if total >= threshold:
          successes += 1
    fraction = float(successes)/samples
    print("Success rate: ", fraction)


def main():
    parser = argparse.ArgumentParser(description='Simulates weighted hypergeometric distributions')
    parser.add_argument('-p', '--population', type=int, help='Total population size')
    parser.add_argument('-s', '--sample', type=int, help='Sample size')
    parser.add_argument('-t', '--threshold', type=int, help='Desired success threshold')
    parser.add_argument('--p1', type=int, help='Size of population worth 1 success')
    parser.add_argument('--p2', type=int, help='Size of population worth 2 successes')
    parser.add_argument('--p3', type=int, help='Size of population worth 3 successes')
    args = parser.parse_args()

    population = []
    remaining = args.population
    if args.p1:
        remaining -= args.p1
        for _ in range(args.p1):
            population.append(1)
    if args.p2:
        remaining -= args.p2
        for _ in range(args.p2):
            population.append(2)
    if args.p3:
        remaining -= args.p3
        for _ in range(args.p3):
            population.append(3)
    for _ in range(remaining):
        population.append(0)

    simulate(population, args.sample, args.threshold)

if __name__ == '__main__':
    main()

