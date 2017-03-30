# Copyright (C) 2016 Huang MaChi at Chongqing University
# of Posts and Telecommunications, Chongqing, China.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import re
import matplotlib.pyplot as plt
import numpy as np


parser = argparse.ArgumentParser(description="Plot EFattree experiments' results")
parser.add_argument('--k', dest='k', type=int, default=4, choices=[4, 8], help="Switch fanout number")
parser.add_argument('--duration', dest='duration', type=int, default=60, help="Duration (sec) for each iperf traffic generation")
parser.add_argument('--dir', dest='out_dir', help="Directory to store outputs")
args = parser.parse_args()


def read_file_1(file_name, delim=','):
	"""
		Read the bwmng.txt file.
	"""
	read_file = open(file_name, 'r')
	lines = read_file.xreadlines()
	lines_list = []
	for line in lines:
		line_list = line.strip().split(delim)
		lines_list.append(line_list)
	read_file.close()

	# Remove the last second's statistics, because they are mostly not intact.
	last_second = lines_list[-1][0]
	_lines_list = lines_list[:]
	for line in _lines_list:
		if line[0] == last_second:
			lines_list.remove(line)

	return lines_list

def read_file_2(file_name):
	"""
		Read the first_packets.txt and successive_packets.txt file.
	"""
	read_file = open(file_name, 'r')
	lines = read_file.xreadlines()
	lines_list = []
	for line in lines:
		if line.startswith('rtt') or line.endswith('ms\n'):
			lines_list.append(line)
	read_file.close()
	return lines_list

def calculate_average(value_list):
	average_value = sum(map(float, value_list)) / len(value_list)
	return average_value

def get_throughput(throughput, traffic, app, input_file):
	"""
		csv output format:
		(Type rate)
		unix_timestamp;iface_name;bytes_out/s;bytes_in/s;bytes_total/s;bytes_in;bytes_out;packets_out/s;packets_in/s;packets_total/s;packets_in;packets_out;errors_out/s;errors_in/s;errors_in;errors_out\n
		(Type svg, sum, max)
		unix timestamp;iface_name;bytes_out;bytes_in;bytes_total;packets_out;packets_in;packets_total;errors_out;errors_in\n
		The bwm-ng mode used is 'rate'.

		throughput = {
						'stag1_0.5_0.3':
						{
							'realtime_bisection_bw': {'EFattree':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'realtime_throughput': {'EFattree':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'accumulated_throughput': {'EFattree':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'normalized_total_throughput': {'EFattree':x%, 'ECMP':x%, ...}
						},
						'stag2_0.5_0.3':
						{
							'realtime_bisection_bw': {'EFattree':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'realtime_throughput': {'EFattree':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'accumulated_throughput': {'EFattree':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'normalized_total_throughput': {'EFattree':x%, 'ECMP':x%, ...}
						},
						...
					}
	"""
	full_bisection_bw = 10.0 * (args.k ** 3 / 4)   # (unit: Mbit/s)
	lines_list = read_file_1(input_file)
	first_second = int(lines_list[0][0])
	column_bytes_out_rate = 2   # bytes_out/s
	column_bytes_out = 6   # bytes_out

	if app == 'NonBlocking':
		switch = '1001'
	elif app in ['EFattree', 'ECMP', 'PureSDN', 'Hedera']:
		switch = '3[0-9][0-9][0-9]'
	else:
		pass
	sw = re.compile(switch)

	if not throughput.has_key(traffic):
		throughput[traffic] = {}

	if not throughput[traffic].has_key('realtime_bisection_bw'):
		throughput[traffic]['realtime_bisection_bw'] = {}
	if not throughput[traffic].has_key('realtime_throughput'):
		throughput[traffic]['realtime_throughput'] = {}
	if not throughput[traffic].has_key('accumulated_throughput'):
		throughput[traffic]['accumulated_throughput'] = {}
	if not throughput[traffic].has_key('normalized_total_throughput'):
		throughput[traffic]['normalized_total_throughput'] = {}

	if not throughput[traffic]['realtime_bisection_bw'].has_key(app):
		throughput[traffic]['realtime_bisection_bw'][app] = {}
	if not throughput[traffic]['realtime_throughput'].has_key(app):
		throughput[traffic]['realtime_throughput'][app] = {}
	if not throughput[traffic]['accumulated_throughput'].has_key(app):
		throughput[traffic]['accumulated_throughput'][app] = {}
	if not throughput[traffic]['normalized_total_throughput'].has_key(app):
		throughput[traffic]['normalized_total_throughput'][app] = 0

	for i in xrange(args.duration + 1):
		if not throughput[traffic]['realtime_bisection_bw'][app].has_key(i):
			throughput[traffic]['realtime_bisection_bw'][app][i] = 0
		if not throughput[traffic]['realtime_throughput'][app].has_key(i):
			throughput[traffic]['realtime_throughput'][app][i] = 0
		if not throughput[traffic]['accumulated_throughput'][app].has_key(i):
			throughput[traffic]['accumulated_throughput'][app][i] = 0

	for row in lines_list:
		iface_name = row[1]
		if iface_name not in ['total', 'lo', 'eth0', 'enp0s3', 'enp0s8', 'docker0']:
			if switch == '3[0-9][0-9][0-9]':
				if sw.match(iface_name):
					if int(iface_name[-1]) > args.k / 2:   # Choose down-going interfaces only.
						if (int(row[0]) - first_second) <= args.duration:   # Take the good values only.
							throughput[traffic]['realtime_bisection_bw'][app][int(row[0]) - first_second] += float(row[column_bytes_out_rate]) * 8.0 / (10 ** 6)   # Mbit/s
							throughput[traffic]['realtime_throughput'][app][int(row[0]) - first_second] += float(row[column_bytes_out]) * 8.0 / (10 ** 6)   # Mbit
			elif switch == '1001':   # Choose all the interfaces. (For NonBlocking Topo only)
				if sw.match(iface_name):
					if (int(row[0]) - first_second) <= args.duration:
						throughput[traffic]['realtime_bisection_bw'][app][int(row[0]) - first_second] += float(row[column_bytes_out_rate]) * 8.0 / (10 ** 6)   # Mbit/s
						throughput[traffic]['realtime_throughput'][app][int(row[0]) - first_second] += float(row[column_bytes_out]) * 8.0 / (10 ** 6)   # Mbit
			else:
				pass

	for i in xrange(args.duration + 1):
		for j in xrange(i+1):
			throughput[traffic]['accumulated_throughput'][app][i] += throughput[traffic]['realtime_throughput'][app][j]   # Mbit

	throughput[traffic]['normalized_total_throughput'][app] = throughput[traffic]['accumulated_throughput'][app][args.duration] / (full_bisection_bw * args.duration)   # percentage

	return throughput

def get_value_list_1(value_dict, traffic, item, app):
	"""
		Get the values from the "throughput" data structure.
	"""
	value_list = []
	for i in xrange(args.duration + 1):
		value_list.append(value_dict[traffic][item][app][i])
	return value_list

def get_average_bisection_bw(value_dict, traffics, app):
	value_list = []
	for traffic in traffics:
		value_list.append(value_dict[traffic]['accumulated_throughput'][app][args.duration] / float(args.duration))
	return value_list

def get_value_list_2(value_dict, traffics, item, app):
	"""
		Get the values from the "throughput", "first_packet_delay" and "average_delay" data structure.
	"""
	value_list = []
	for traffic in traffics:
		value_list.append(value_dict[traffic][item][app])
	return value_list

def get_delay(delay, traffic, keys, app, input_file):
	"""
		first_packet_delay = {
								'stag1_0.5_0.3':
								{
									'average_first_packet_round_trip_delay': {'EFattree':x, 'ECMP':x, ...},
									'first_packet_loss_rate': {'EFattree':x%, 'ECMP':x%, ...}
								},
								'stag2_0.5_0.3':
								{
									'average_first_packet_round_trip_delay': {'EFattree':x, 'ECMP':x, ...},
									'first_packet_loss_rate': {'EFattree':x%, 'ECMP':x%, ...}
								},
								...
							}

		average_delay = {
							'stag1_0.5_0.3':
							{
								'average_round_trip_delay': {'EFattree':x, 'ECMP':x, ...},
								'packet_loss_rate': {'EFattree':x%, 'ECMP':x%, ...},
								'mean_deviation_of_round_trip_delay': {'EFattree':x%, 'ECMP':x%, ...},
							},
							'stag2_0.5_0.3':
							{
								'average_round_trip_delay': {'EFattree':x, 'ECMP':x, ...},
								'packet_loss_rate': {'EFattree':x%, 'ECMP':x%, ...},
								'mean_deviation_of_round_trip_delay': {'EFattree':x%, 'ECMP':x%, ...},
							},
							...
						}
	"""
	if not delay.has_key(traffic):
		delay[traffic] = {}

	for i in range(len(keys)):
		if not delay[traffic].has_key(keys[i]):
			delay[traffic][keys[i]] = {}

	for i in range(len(keys)):
		if not delay[traffic][keys[i]].has_key(app):
			delay[traffic][keys[i]][app] = 0

	lines_list = read_file_2(input_file)
	total_send = 0
	total_receive = 0
	average_delay_list = []
	if len(keys) == 2:
		for line in lines_list:
			if line.startswith('rtt'):
				average_delay_list.append(float(line.split('/')[4]))
			else:
				total_send += int(line.split(' ')[0])
				total_receive += int(line.split(' ')[3])
		delay[traffic][keys[0]][app] = calculate_average(average_delay_list)
		delay[traffic][keys[1]][app] = float(total_send - total_receive) / total_send
	elif len(keys) == 3:
		mean_deviation_list = []
		for line in lines_list:
			if line.startswith('rtt'):
				average_delay_list.append(float(line.split('/')[4]))
				mean_deviation_list.append(float((line.split('/')[6]).split(' ')[0]))
			else:
				total_send += int(line.split(' ')[0])
				total_receive += int(line.split(' ')[3])
		delay[traffic][keys[0]][app] = calculate_average(average_delay_list)
		delay[traffic][keys[1]][app] = float(total_send - total_receive) / total_send
		delay[traffic][keys[2]][app] = calculate_average(mean_deviation_list)

	return delay

def plot_results():
	"""
		Plot the results:
		1. Plot realtime bisection bandwidth
		2. Plot average bisection bandwidth
		3. Plot accumulated throughput
		4. Plot normalized total throughput
		5. Plot average first-packet round-trip delay of delay-sensitive traffic
		6. Plot first-packet loss rate of delay-sensitive traffic
		7. Plot average packet round-trip delay of delay-sensitive traffic
		8. Plot packet loss rate of delay-sensitive-traffic
		9. Plot mean deviation of round-trip delay of delay-sensitive traffic

		throughput = {
						'stag1_0.5_0.3':
						{
							'realtime_bisection_bw': {'EFattree':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'realtime_throughput': {'EFattree':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'accumulated_throughput': {'EFattree':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'normalized_total_throughput': {'EFattree':x%, 'ECMP':x%, ...}
						},
						'stag2_0.5_0.3':
						{
							'realtime_bisection_bw': {'EFattree':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'realtime_throughput': {'EFattree':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'accumulated_throughput': {'EFattree':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'normalized_total_throughput': {'EFattree':x%, 'ECMP':x%, ...}
						},
						...
					}

		first_packet_delay = {
								'stag1_0.2_0.3':
								{
									'average_first_packet_round_trip_delay': {'EFattree':x, 'ECMP':x, ...},
									'first_packet_loss_rate': {'EFattree':x%, 'ECMP':x%, ...}
								},
								'stag2_0.2_0.3':
								{
									'average_first_packet_round_trip_delay': {'EFattree':x, 'ECMP':x, ...},
									'first_packet_loss_rate': {'EFattree':x%, 'ECMP':x%, ...}
								},
								...
							}

		average_delay = {
							'stag1_0.2_0.3':
							{
								'average_round_trip_delay': {'EFattree':x, 'ECMP':x, ...},
								'packet_loss_rate': {'EFattree':x%, 'ECMP':x%, ...},
								'mean_deviation_of_round_trip_delay': {'EFattree':x%, 'ECMP':x%, ...},
							},
							'stag2_0.2_0.3':
							{
								'average_round_trip_delay': {'EFattree':x, 'ECMP':x, ...},
								'packet_loss_rate': {'EFattree':x%, 'ECMP':x%, ...},
								'mean_deviation_of_round_trip_delay': {'EFattree':x%, 'ECMP':x%, ...},
							},
							...
						}
	"""
	full_bisection_bw = 10.0 * (args.k ** 3 / 4)   # (unit: Mbit/s)
	utmost_throughput = full_bisection_bw * args.duration
	_traffics = "stag1_0.5_0.3 stag2_0.5_0.3 stag1_0.6_0.2 stag2_0.6_0.2 stag1_0.7_0.2 stag2_0.7_0.2 stag1_0.8_0.1 stag2_0.8_0.1"
	# _traffics = "stag_0.2_0.3 stag_0.3_0.3 stag_0.4_0.3 stag_0.5_0.3 stag_0.6_0.2 stag_0.7_0.2 stag_0.8_0.1 random"
	traffics = _traffics.split(' ')
	apps = ['EFattree', 'ECMP', 'PureSDN', 'Hedera']
	throughput = {}
	first_packet_delay = {}
	average_delay = {}

	for traffic in traffics:
		for app in apps:
			bwmng_file = args.out_dir + '/%s/%s/bwmng.txt' % (traffic, app)
			throughput = get_throughput(throughput, traffic, app, bwmng_file)
			keys1 = ['average_first_packet_round_trip_delay', 'first_packet_loss_rate']
			keys2 = ['average_round_trip_delay', 'packet_loss_rate', 'mean_deviation_of_round_trip_delay']
			first_packet_file = args.out_dir + '/%s/%s/first_packets.txt' % (traffic, app)
			first_packet_delay = get_delay(first_packet_delay, traffic, keys1, app, first_packet_file)
			successive_packets_file = args.out_dir + '/%s/%s/successive_packets.txt' % (traffic, app)
			average_delay = get_delay(average_delay, traffic, keys2, app, successive_packets_file)

	# 1. Plot realtime throughput.
	item = 'realtime_bisection_bw'
	fig = plt.figure()
	fig.set_size_inches(12, 16)
	num_subplot = len(traffics)
	num_raw = 4
	num_column = num_subplot / num_raw
	NO_subplot = 1
	x = np.arange(0, args.duration + 1)
	for traffic in traffics:
		plt.subplot(num_raw, num_column, NO_subplot)
		y1 = get_value_list_1(throughput, traffic, item, 'EFattree')
		y2 = get_value_list_1(throughput, traffic, item, 'ECMP')
		y3 = get_value_list_1(throughput, traffic, item, 'Hedera')
		y4 = get_value_list_1(throughput, traffic, item, 'PureSDN')
		plt.plot(x, y1, 'r-', linewidth=2, label="EFattree")
		plt.plot(x, y2, 'b-', linewidth=2, label="ECMP")
		plt.plot(x, y3, 'y-', linewidth=2, label="Hedera")
		plt.plot(x, y4, 'g-', linewidth=2, label="PureSDN")
		plt.title('%s' % traffic, fontsize='x-large')
		plt.xlabel('Time (s)', fontsize='x-large')
		plt.xlim(0, args.duration)
		plt.xticks(np.arange(0, args.duration + 1, 10))
		plt.ylabel('Realtime Throughput\n(Mbps)', fontsize='x-large')
		plt.ylim(0, full_bisection_bw)
		plt.yticks(np.linspace(0, full_bisection_bw, 11))
		plt.legend(loc='upper right', ncol=len(apps), fontsize='xx-small')
		plt.grid(True)
		NO_subplot += 1
	plt.subplots_adjust(top=0.95, bottom=0.05, left=0.1, right=0.95, hspace=0.35, wspace=0.35)
	plt.savefig(args.out_dir + '/1.realtime_throughput.png')

	# 2. Plot average throughput.
	fig = plt.figure()
	fig.set_size_inches(12, 6)
	num_groups = len(traffics)
	num_bar = len(apps)
	EFattree_value_list = get_average_bisection_bw(throughput, traffics, 'EFattree')
	ECMP_value_list = get_average_bisection_bw(throughput, traffics, 'ECMP')
	Hedera_value_list = get_average_bisection_bw(throughput, traffics, 'Hedera')
	PureSDN_value_list = get_average_bisection_bw(throughput, traffics, 'PureSDN')
	index = np.arange(num_groups) + 0.15
	bar_width = 0.15
	plt.bar(index + 0 * bar_width, EFattree_value_list, bar_width, color='r', label='EFattree')
	plt.bar(index + 1 * bar_width, ECMP_value_list, bar_width, color='b', label='ECMP')
	plt.bar(index + 2 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
	plt.bar(index + 3 * bar_width, PureSDN_value_list, bar_width, color='g', label='PureSDN')
	plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='small')
	plt.ylabel('Average Throughput\n(Mbps)', fontsize='x-large')
	plt.ylim(0, full_bisection_bw)
	plt.yticks(np.linspace(0, full_bisection_bw, 11))
	plt.legend(loc='upper right', ncol=len(apps), fontsize='small')
	plt.grid(axis='y')
	plt.savefig(args.out_dir + '/2.average_throughput.png')

	# 3. Plot accumulated throughput.
	item = 'accumulated_throughput'
	fig = plt.figure()
	fig.set_size_inches(12, 16)
	num_subplot = len(traffics)
	num_raw = 4
	num_column = num_subplot / num_raw
	NO_subplot = 1
	x = np.arange(0, args.duration + 1)
	for traffic in traffics:
		plt.subplot(num_raw, num_column, NO_subplot)
		y1 = get_value_list_1(throughput, traffic, item, 'EFattree')
		y2 = get_value_list_1(throughput, traffic, item, 'ECMP')
		y3 = get_value_list_1(throughput, traffic, item, 'Hedera')
		y4 = get_value_list_1(throughput, traffic, item, 'PureSDN')
		plt.plot(x, y1, 'r-', linewidth=2, label="EFattree")
		plt.plot(x, y2, 'b-', linewidth=2, label="ECMP")
		plt.plot(x, y3, 'y-', linewidth=2, label="Hedera")
		plt.plot(x, y4, 'g-', linewidth=2, label="PureSDN")
		plt.title('%s' % traffic, fontsize='x-large')
		plt.xlabel('Time (s)', fontsize='x-large')
		plt.xlim(0, args.duration)
		plt.xticks(np.arange(0, args.duration + 1, 10))
		plt.ylabel('Accumulated Throughput\n(Mbit)', fontsize='x-large')
		plt.ylim(0, utmost_throughput)
		plt.yticks(np.linspace(0, utmost_throughput, 11))
		plt.legend(loc='upper left', fontsize='medium')
		plt.grid(True)
		NO_subplot += 1
	plt.subplots_adjust(top=0.95, bottom=0.05, left=0.1, right=0.95, hspace=0.35, wspace=0.35)
	plt.savefig(args.out_dir + '/3.accumulated_throughput.png')

	# 4. Plot normalized total throughput.
	item = 'normalized_total_throughput'
	fig = plt.figure()
	fig.set_size_inches(12, 6)
	num_groups = len(traffics)
	num_bar = len(apps)
	EFattree_value_list = get_value_list_2(throughput, traffics, item, 'EFattree')
	ECMP_value_list = get_value_list_2(throughput, traffics, item, 'ECMP')
	Hedera_value_list = get_value_list_2(throughput, traffics, item, 'Hedera')
	PureSDN_value_list = get_value_list_2(throughput, traffics, item, 'PureSDN')
	index = np.arange(num_groups) + 0.15
	bar_width = 0.15
	plt.bar(index + 0 * bar_width, EFattree_value_list, bar_width, color='r', label='EFattree')
	plt.bar(index + 1 * bar_width, ECMP_value_list, bar_width, color='b', label='ECMP')
	plt.bar(index + 2 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
	plt.bar(index + 3 * bar_width, PureSDN_value_list, bar_width, color='g', label='PureSDN')
	plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='small')
	plt.ylabel('Normalized Total Throughput\n', fontsize='x-large')
	plt.ylim(0, 1)
	plt.yticks(np.linspace(0, 1, 11))
	plt.legend(loc='upper right', ncol=len(apps), fontsize='small')
	plt.grid(axis='y')
	plt.savefig(args.out_dir + '/4.normalized_total_throughput.png')

	# 5. Plot average first-packet round-trip delay of delay-sensitive traffic.
	item = 'average_first_packet_round_trip_delay'
	fig = plt.figure()
	fig.set_size_inches(12, 6)
	num_groups = len(traffics)
	num_bar = len(apps)
	EFattree_value_list = get_value_list_2(first_packet_delay, traffics, item, 'EFattree')
	PureSDN_value_list = get_value_list_2(first_packet_delay, traffics, item, 'PureSDN')
	ECMP_value_list = get_value_list_2(first_packet_delay, traffics, item, 'ECMP')
	Hedera_value_list = get_value_list_2(first_packet_delay, traffics, item, 'Hedera')
	index = np.arange(num_groups) + 0.15
	bar_width = 0.15
	plt.bar(index, EFattree_value_list, bar_width, color='r', label='EFattree')
	plt.bar(index + 1 * bar_width, PureSDN_value_list, bar_width, color='g', label='PureSDN')
	plt.bar(index + 2 * bar_width, ECMP_value_list, bar_width, color='b', label='ECMP')
	plt.bar(index + 3 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
	plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='small')
	plt.ylabel('Average First-packet Round-trip Delay\nof Delay-sensitive Traffic\n(ms)', fontsize='large')
	plt.legend(loc='upper right', ncol=len(apps), fontsize='small')
	plt.grid(axis='y')
	plt.savefig(args.out_dir + '/5.average_first_packet_round_trip_delay.png')

	# 5-2. Plot average first-packet round-trip delay of delay-sensitive traffic. (Without ECMP and Hedera)
	item = 'average_first_packet_round_trip_delay'
	fig = plt.figure()
	fig.set_size_inches(12, 6)
	num_groups = len(traffics)
	num_bar = len(apps) - 2
	EFattree_value_list = get_value_list_2(first_packet_delay, traffics, item, 'EFattree')
	PureSDN_value_list = get_value_list_2(first_packet_delay, traffics, item, 'PureSDN')
	# ECMP_value_list = get_value_list_2(first_packet_delay, traffics, item, 'ECMP')
	# Hedera_value_list = get_value_list_2(first_packet_delay, traffics, item, 'Hedera')
	index = np.arange(num_groups) + 0.15
	bar_width = 0.15
	plt.bar(index, EFattree_value_list, bar_width, color='r', label='EFattree')
	plt.bar(index + 1 * bar_width, PureSDN_value_list, bar_width, color='g', label='PureSDN')
	# plt.bar(index + 2 * bar_width, ECMP_value_list, bar_width, color='b', label='ECMP')
	# plt.bar(index + 3 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
	plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='small')
	plt.ylabel('Average First-packet Round-trip Delay\nof Delay-sensitive Traffic\n(ms)', fontsize='large')
	plt.legend(loc='upper right', ncol=len(apps)-2, fontsize='small')
	plt.grid(axis='y')
	plt.savefig(args.out_dir + '/5-2.average_first_packet_round_trip_delay.png')

	# 6. Plot first-packet loss rate of delay-sensitive traffic.
	item = 'first_packet_loss_rate'
	fig = plt.figure()
	fig.set_size_inches(12, 6)
	num_groups = len(traffics)
	num_bar = len(apps)
	EFattree_value_list = get_value_list_2(first_packet_delay, traffics, item, 'EFattree')
	PureSDN_value_list = get_value_list_2(first_packet_delay, traffics, item, 'PureSDN')
	ECMP_value_list = get_value_list_2(first_packet_delay, traffics, item, 'ECMP')
	Hedera_value_list = get_value_list_2(first_packet_delay, traffics, item, 'Hedera')
	index = np.arange(num_groups) + 0.15
	bar_width = 0.15
	plt.bar(index, EFattree_value_list, bar_width, color='r', label='EFattree')
	plt.bar(index + 1 * bar_width, PureSDN_value_list, bar_width, color='g', label='PureSDN')
	plt.bar(index + 2 * bar_width, ECMP_value_list, bar_width, color='b', label='ECMP')
	plt.bar(index + 3 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
	plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='small')
	plt.ylabel('First-packet Loss Rate of\nDelay-sensitive Traffic\n', fontsize='large')
	# plt.ylim(0, 1)
	# plt.yticks(np.linspace(0, 1, 11))
	plt.legend(loc='upper right', ncol=len(apps), fontsize='small')
	plt.grid(axis='y')
	plt.savefig(args.out_dir + '/6.first_packet_loss_rate.png')

	# 6-2. Plot first-packet loss rate of delay-sensitive traffic. (Without ECMP and Hedera)
	item = 'first_packet_loss_rate'
	fig = plt.figure()
	fig.set_size_inches(12, 6)
	num_groups = len(traffics)
	num_bar = len(apps) - 2
	EFattree_value_list = get_value_list_2(first_packet_delay, traffics, item, 'EFattree')
	PureSDN_value_list = get_value_list_2(first_packet_delay, traffics, item, 'PureSDN')
	# ECMP_value_list = get_value_list_2(first_packet_delay, traffics, item, 'ECMP')
	# Hedera_value_list = get_value_list_2(first_packet_delay, traffics, item, 'Hedera')
	index = np.arange(num_groups) + 0.15
	bar_width = 0.15
	plt.bar(index, EFattree_value_list, bar_width, color='r', label='EFattree')
	plt.bar(index + 1 * bar_width, PureSDN_value_list, bar_width, color='g', label='PureSDN')
	# plt.bar(index + 2 * bar_width, ECMP_value_list, bar_width, color='b', label='ECMP')
	# plt.bar(index + 3 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
	plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='small')
	plt.ylabel('First-packet Loss Rate of\nDelay-sensitive Traffic\n', fontsize='large')
	# plt.ylim(0, 1)
	# plt.yticks(np.linspace(0, 1, 11))
	plt.legend(loc='upper right', ncol=len(apps)-2, fontsize='small')
	plt.grid(axis='y')
	plt.savefig(args.out_dir + '/6-2.first_packet_loss_rate.png')

	# 7. Plot average packet round-trip delay of delay-sensitive traffic.
	item = 'average_round_trip_delay'
	fig = plt.figure()
	fig.set_size_inches(12, 6)
	num_groups = len(traffics)
	num_bar = len(apps)
	EFattree_value_list = get_value_list_2(average_delay, traffics, item, 'EFattree')
	PureSDN_value_list = get_value_list_2(average_delay, traffics, item, 'PureSDN')
	ECMP_value_list = get_value_list_2(average_delay, traffics, item, 'ECMP')
	Hedera_value_list = get_value_list_2(average_delay, traffics, item, 'Hedera')
	index = np.arange(num_groups) + 0.15
	bar_width = 0.15
	plt.bar(index, EFattree_value_list, bar_width, color='r', label='EFattree')
	plt.bar(index + 1 * bar_width, PureSDN_value_list, bar_width, color='g', label='PureSDN')
	plt.bar(index + 2 * bar_width, ECMP_value_list, bar_width, color='b', label='ECMP')
	plt.bar(index + 3 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
	plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='small')
	plt.ylabel('Average Packet Round-trip Delay of\nDelay-sensitive Traffic\n(ms)', fontsize='large')
	plt.legend(loc='upper right', ncol=len(apps), fontsize='small')
	plt.grid(axis='y')
	plt.savefig(args.out_dir + '/7.average_round_trip_delay.png')

	# 7-2. Plot average packet round-trip delay of delay-sensitive traffic. (Without ECMP and Hedera)
	item = 'average_round_trip_delay'
	fig = plt.figure()
	fig.set_size_inches(12, 6)
	num_groups = len(traffics)
	num_bar = len(apps) -  2
	EFattree_value_list = get_value_list_2(average_delay, traffics, item, 'EFattree')
	PureSDN_value_list = get_value_list_2(average_delay, traffics, item, 'PureSDN')
	# ECMP_value_list = get_value_list_2(average_delay, traffics, item, 'ECMP')
	# Hedera_value_list = get_value_list_2(average_delay, traffics, item, 'Hedera')
	index = np.arange(num_groups) + 0.15
	bar_width = 0.15
	plt.bar(index, EFattree_value_list, bar_width, color='r', label='EFattree')
	plt.bar(index + 1 * bar_width, PureSDN_value_list, bar_width, color='g', label='PureSDN')
	# plt.bar(index + 2 * bar_width, ECMP_value_list, bar_width, color='b', label='ECMP')
	# plt.bar(index + 3 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
	plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='small')
	plt.ylabel('Average Packet Round-trip Delay of\nDelay-sensitive Traffic\n(ms)', fontsize='large')
	plt.legend(loc='upper right', ncol=len(apps)-2, fontsize='small')
	plt.grid(axis='y')
	plt.savefig(args.out_dir + '/7-2.average_round_trip_delay.png')

	# 8. Plot packet loss rate of delay-sensitive traffic.
	item = 'packet_loss_rate'
	fig = plt.figure()
	fig.set_size_inches(12, 6)
	num_groups = len(traffics)
	num_bar = len(apps)
	EFattree_value_list = get_value_list_2(average_delay, traffics, item, 'EFattree')
	PureSDN_value_list = get_value_list_2(average_delay, traffics, item, 'PureSDN')
	ECMP_value_list = get_value_list_2(average_delay, traffics, item, 'ECMP')
	Hedera_value_list = get_value_list_2(average_delay, traffics, item, 'Hedera')
	index = np.arange(num_groups) + 0.15
	bar_width = 0.15
	plt.bar(index, EFattree_value_list, bar_width, color='r', label='EFattree')
	plt.bar(index + 1 * bar_width, PureSDN_value_list, bar_width, color='g', label='PureSDN')
	plt.bar(index + 2 * bar_width, ECMP_value_list, bar_width, color='b', label='ECMP')
	plt.bar(index + 3 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
	plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='small')
	plt.ylabel('Packet Loss Rate of\nDelay-sensitive Traffic\n', fontsize='large')
	# plt.ylim(0, 1)
	# plt.yticks(np.linspace(0, 1, 11))
	plt.legend(loc='upper right', ncol=len(apps), fontsize='small')
	plt.grid(axis='y')
	plt.savefig(args.out_dir + '/8.packet_loss_rate.png')

	# 8-2. Plot packet loss rate of delay-sensitive traffic. (Without ECMP and Hedera)
	item = 'packet_loss_rate'
	fig = plt.figure()
	fig.set_size_inches(12, 6)
	num_groups = len(traffics)
	num_bar = len(apps) - 2
	EFattree_value_list = get_value_list_2(average_delay, traffics, item, 'EFattree')
	PureSDN_value_list = get_value_list_2(average_delay, traffics, item, 'PureSDN')
	# ECMP_value_list = get_value_list_2(average_delay, traffics, item, 'ECMP')
	# Hedera_value_list = get_value_list_2(average_delay, traffics, item, 'Hedera')
	index = np.arange(num_groups) + 0.15
	bar_width = 0.15
	plt.bar(index, EFattree_value_list, bar_width, color='r', label='EFattree')
	plt.bar(index + 1 * bar_width, PureSDN_value_list, bar_width, color='g', label='PureSDN')
	# plt.bar(index + 2 * bar_width, ECMP_value_list, bar_width, color='b', label='ECMP')
	# plt.bar(index + 3 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
	plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='small')
	plt.ylabel('Packet Loss Rate of\nDelay-sensitive Traffic\n', fontsize='large')
	# plt.ylim(0, 1)
	# plt.yticks(np.linspace(0, 1, 11))
	plt.legend(loc='upper right', ncol=len(apps)-2, fontsize='small')
	plt.grid(axis='y')
	plt.savefig(args.out_dir + '/8-2.packet_loss_rate.png')

	# 9. Plot mean deviation of round-trip delay of delay-sensitive traffic.
	item = 'mean_deviation_of_round_trip_delay'
	fig = plt.figure()
	fig.set_size_inches(12, 6)
	num_groups = len(traffics)
	num_bar = len(apps)
	EFattree_value_list = get_value_list_2(average_delay, traffics, item, 'EFattree')
	PureSDN_value_list = get_value_list_2(average_delay, traffics, item, 'PureSDN')
	ECMP_value_list = get_value_list_2(average_delay, traffics, item, 'ECMP')
	Hedera_value_list = get_value_list_2(average_delay, traffics, item, 'Hedera')
	index = np.arange(num_groups) + 0.15
	bar_width = 0.15
	plt.bar(index, EFattree_value_list, bar_width, color='r', label='EFattree')
	plt.bar(index + 1 * bar_width, PureSDN_value_list, bar_width, color='g', label='PureSDN')
	plt.bar(index + 2 * bar_width, ECMP_value_list, bar_width, color='b', label='ECMP')
	plt.bar(index + 3 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
	plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='small')
	plt.ylabel('Mean Deviation of Round-trip Delay\nof Delay-sensitive Traffic\n(ms)', fontsize='large')
	plt.legend(loc='upper right', ncol=len(apps), fontsize='small')
	plt.grid(axis='y')
	plt.savefig(args.out_dir + '/9.mean_deviation_of_round_trip_delay.png')

	# 9-2. Plot mean deviation of round-trip delay of delay-sensitive traffic. (Without ECMP and Hedera)
	item = 'mean_deviation_of_round_trip_delay'
	fig = plt.figure()
	fig.set_size_inches(12, 6)
	num_groups = len(traffics)
	num_bar = len(apps) - 2
	EFattree_value_list = get_value_list_2(average_delay, traffics, item, 'EFattree')
	PureSDN_value_list = get_value_list_2(average_delay, traffics, item, 'PureSDN')
	# ECMP_value_list = get_value_list_2(average_delay, traffics, item, 'ECMP')
	# Hedera_value_list = get_value_list_2(average_delay, traffics, item, 'Hedera')
	index = np.arange(num_groups) + 0.15
	bar_width = 0.15
	plt.bar(index, EFattree_value_list, bar_width, color='r', label='EFattree')
	plt.bar(index + 1 * bar_width, PureSDN_value_list, bar_width, color='g', label='PureSDN')
	# plt.bar(index + 2 * bar_width, ECMP_value_list, bar_width, color='b', label='ECMP')
	# plt.bar(index + 3 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
	plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='small')
	plt.ylabel('Mean Deviation of Round-trip Delay\nof Delay-sensitive Traffic\n(ms)', fontsize='large')
	plt.legend(loc='upper right', ncol=len(apps)-2, fontsize='small')
	plt.grid(axis='y')
	plt.savefig(args.out_dir + '/9-2.mean_deviation_of_round_trip_delay.png')

if __name__ == '__main__':
	plot_results()
