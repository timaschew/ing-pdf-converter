import os
import sys
import json
import re
from PyPDF2 import PdfReader

START_HEADER = "Valuta"

END_HEADER = "Neuer Saldo"
END_HEADER_AFTER_1 = "Kunden-Information" # next line after END_HEADER
END_HEADER_AFTER_2 = "Kontoauszug" # next line after END_HEADER

STOP_HEADERS = [
	'34GKKA', # Girokonto
	'34GIRO', # Girokonto
	'34STAN', # Aktiendepot
	'34EXMU', # Extrakonto
	'34SPAR', # VL-Sparkonto
	'34PKKA' # Rahmenkredit
]

# German Umlaute Encoding
c = [
	["\u00df", 'ß'],
	["\u00e4", 'ä'],
	["\u00f6", 'ö'],
	["\u00fc", 'ü'],
	["\u00c4", 'Ä'],
	["\u00d6", 'Ö'],
	["\u00dc", 'Ü']
]

TYPES = [
	"Gutschrift",
	"Ueberweisung",
	"Lastschrift",
	"Bezuege",
	"Gehalt/Rente",
	"Dauerauftrag/Terminueberw.",
	"Entgelt",
	"Retoure",
	"Abbuchung"
]
MANDATE_PREFIX = "Mandat"
REFERENCE_PREFIX = "Referenz"

CURRENCY = "EUR"

CSV_COLUMNS = [
"Buchung",
"Valuta",
"Auftraggeber/Empfänger",
"Buchungstext",
"Verwendungszweck",
"Referenz",
"Mandat",
"Saldo",
"Währung",
"Betrag",
"Währung"
]

CSV_SEP = ";"

META_PATTERN = r"Frankfurt am Main\nDatum\s(\d{2}\.\d{2}\.\d{4})\n.*\n.*\nAlter Saldo\s([\d.,]*)\sEuro\nNeuer Saldo\s([\d.,]*)\sEuro\nIBAN"


print(sys.argv)

def main():
	if len(sys.argv) > 1:
		if os.path.isfile(sys.argv[1]):
			extract_pdf(sys.argv[1])
		else:
			for entry in os.scandir(sys.argv[1]):
				if ".pdf" in entry.name:
					file_prefix = os.path.splitext(entry.name)[0]
					alternative_file = os.path.join(sys.argv[1], file_prefix + ".txt")
					if os.path.isfile(alternative_file):
						print(f"Scanning failover file: {file_prefix + '.txt'}")
						extract_pdf(alternative_file)
					else:
						print(f"Scanning file: {entry.name}")
						extract_pdf(os.path.join(sys.argv[1], entry.name))
	else:
		print("No path was given")
		sys.exit(1)

def parse_float(string_value):
	cleaned_value = parse_amount(string_value)
	return float(cleaned_value.replace(".", "").replace(",", "."))

def parse_amount(amount):
	# sometimes an amount is parsed with 3 digits after the comma
	# because there small superscript digit, this digit needs to be removed
	[ints, fraction] = amount.split(",")
	return f"{ints},{fraction[:2]}"

def format_saldo(saldo):
	tmp = "{:.2f}".format(saldo).replace(".", ",")
	[ints, other] = tmp.split(",")
	int_list = list(ints)
	new_ints = []
	while len(int_list) > 0:
		new_ints[:0] = [int_list.pop()]
		if len(int_list) == 0:
			pass
		else:
			if len(new_ints) == 3 or len(new_ints) == 7 or len(new_ints) == 11:
				new_ints[:0] = ["."]

	return "".join(new_ints) + "," + other


def format_description(t):
	reference = ""
	mandate = ""

	# if t.get("referenz") is not None:
	# 	reference = f"|Referenz: {t['referenz']}"
	# if t.get("mandat") is not None:
	# 	mandate = f"|Mandat: {t['mandat']}"

	return f"{''.join(t['zweck'])}{reference}{mandate}"



def save_as_json(transactions, file_path, meta):
	output = {
		"meta": meta,
		"transactions": transactions 
	}
	file_prefix = os.path.splitext(file_path)[0]
	with open(file_prefix + ".json", "w", encoding = "utf8") as fh:
		json.dump(output, fh, indent = 4, ensure_ascii = False)

def save_as_csv(transactions, file_path, meta):
	file_prefix = os.path.splitext(file_path)[0]
	with open(file_prefix +  ".csv", "w", encoding = "utf8") as fh:
		fh.write(CSV_SEP.join(CSV_COLUMNS) + "\n")

		saldo = parse_float(meta["saldo_alt"])
		for t in transactions:
			if t.get("buchung") is None:
				continue

			saldo += parse_float(t["betrag"])
			row = [
				t["buchung"],
				t["valuta"],
				t["konto"],
				t["typ"],
				format_description(t),
				t.get("referenz", ""),
				t.get("mandat", ""),
				format_saldo(saldo),
				CURRENCY,
				parse_amount(t["betrag"]),
				CURRENCY
			]
			fh.write(CSV_SEP.join(row) + "\n")


		if abs(parse_float(meta["saldo_neu"]) - saldo) > 0.009: # rounding treshold
			print(f"Alter Saldo: {parse_float(meta['saldo_neu'])} + Tranksaktionen stimmt nicht überein mit neuem Saldo: {saldo}")
			print("Unterschied", parse_float(meta["saldo_neu"]) - saldo)
			sys.exit(1)

def extract_meta(lines):
	pattern = re.compile(META_PATTERN, re.MULTILINE)
	matched = pattern.search(lines)
	if matched is not None:
		meta = {}
		meta["datum"] = matched[1]
		meta["saldo_alt"] = matched[2]
		meta["saldo_neu"] = matched[3]
		return meta

def find_stop_header(lines):
	for line in lines:
		for stop_header in STOP_HEADERS:
			if stop_header in line:
				return stop_header

	raise Exception("No stop header was found")

# First convert PDF to TXT, then parse TXT
def extract_pdf(file_path):
	# check if txt file exist, faster processing if you repeat conversion for the same file
	if ".txt" in file_path:
		with open(file_path, "r") as fh:
			lines = fh.readlines()

		stop_header = find_stop_header(lines)
		transactions = extract_lines(lines, stop_header)
		meta = extract_meta("".join(lines))
		
		#print("start analyzing")
		save_as_json(transactions, file_path, meta)
		save_as_csv(transactions, file_path, meta)

		return 

	reader = PdfReader(file_path)

	text = ""
	for page in reader.pages:
		text += page.extract_text() + "\n"

	with open("raw.txt", "w") as fh:
		fh.write(text)

	lines = []
	for page in reader.pages:
		lines += page.extract_text().split("\n")

	stop_header = find_stop_header(lines)
	transactions = extract_lines(lines, stop_header)
	meta = extract_meta("\n".join(lines))

	save_as_json(transactions, file_path, meta)
	save_as_csv(transactions, file_path, meta)


def is_first_line_candidate(line):
	parts = line.split(" ")
	if len(parts) > 1 and parts[1] in TYPES and re.match("^\d{2}\.\d{2}\.\d{4}", line[0:10]):
		return True

	return False


def clean_line(line):
	# for r in REPLACEMENTS:
	# 	line = line.replace(r[0], r[1])

	return line.strip()


def extract_lines(raw_lines, stop_header):
	parsing = False
	transactions = []
	tmp_transaction = None
	total_lines = 0
	loop_line_number = 0

	for raw_line in raw_lines:
		total_lines = total_lines + 1
		raw_line = raw_line.strip()

		if raw_line == "":
			continue

		try:
			next_raw_line = raw_lines[total_lines].strip()
		except:
			pass

		
		if len(raw_line.split(stop_header)) > 1:
			line = raw_line.split(stop_header)[0]
		else: 
			line = raw_line

		parts = line.split(" ")

		if parsing:

			#print(f" TOTAL # {total_lines} | LOKAL # {loop_line_number} | {line}")

			if END_HEADER in raw_line and (END_HEADER_AFTER_1 in next_raw_line or END_HEADER_AFTER_2 in next_raw_line):
				#print("finish parsing")
				transactions.append(tmp_transaction)
				return transactions

			if is_first_line_candidate(line):
				if tmp_transaction is not None:
					if tmp_transaction.get("valuta") is None:
						# it's 2nd line, but looks like 1st, just pass
						pass
					else:
						# valuta is already set, it's the next transaction
						#print("saving previous transaction", tmp_transaction)
						transactions.append(tmp_transaction)
						tmp_transaction = {}	
						loop_line_number = 0
				else:
					# tmp_transaction is None -> first transaction 
					tmp_transaction = {}

			loop_line_number = loop_line_number + 1
			if loop_line_number == 1:
				tmp_transaction["buchung"] = parts[0]
				tmp_transaction["typ"] = parts[1]
				tmp_transaction["betrag"] = parts.pop()
				tmp_transaction["konto"] = " ".join(parts[2:])
				tmp_transaction["zweck"] = []
			elif loop_line_number == 2:
				tmp_transaction["valuta"] = parts[0]
				if line != "":
					#print("adding description (2nd line)")
					tmp_transaction["zweck"].append(" ".join(parts[1:]))
			else:
				# either line 3 or 4 or a new transaction
				if MANDATE_PREFIX in line:
					tmp_transaction["mandat"] = " ".join(parts[1:])
					#print("saving mandate")
				elif REFERENCE_PREFIX in line:
					tmp_transaction["referenz"] = " ".join(parts[1:])
					#print("saving mandate")
				else:
					if line != "":
						#print(f"adding description from #{loop_line_number}")
						tmp_transaction["zweck"].append(line)
					else:
						pass
						#print("skipping empty line")

				
		if START_HEADER in raw_line:
			# start
			parsing = True
			#print("starting at ", total_lines, " with content: ", raw_line)

		elif stop_header in raw_line:
			# stop
			#print("stopping at ", total_lines, " with content: ", raw_line)
			parsing = False
			transactions.append(tmp_transaction)
			tmp_transaction = {}
			loop_line_number = 0

	return transactions

if __name__ == "__main__":
    main()
