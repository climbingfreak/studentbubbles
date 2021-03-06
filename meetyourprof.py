from util.meetyourprofoptimization import solve_meet_prof_optimization
import util.constants
import numpy as np
import json
import heapq
from classes.professordate import Professor
from datetime import date

inputdata = "data/studenten6.json"
inputprofs = "data/professoren.json"

# If False, students in dates with less than 6 participants are systematically shifted from dates with less students to dates with more students.
# If True, students in dates with less than 6 participants are randomly distributed
RAND_SORT = False

ONLY_FIRST_WEEK = False
OPTIMISE_DATES = True
EXCLUDE_WEEKS = [1, 4]


#### DATE DATA
# parse json input to numpy format
with open(inputdata) as input:
    exportdata = json.load(input)

# define the data
prefs = []
studids = []
fachsems = []
orig_prefs = []

# get data from json file
for key in exportdata:
    stud = exportdata[key]

    pref = stud['prefs']
    id = stud['id']
    fachsem = stud['fachsem']

    orig_prefs.append(pref)

    # modify weights for 1st and 3rd semester
    if fachsem == "1":
        for i in range(len(pref)):
            pref[i] += 2

    prefs.append(pref)
    fachsems.append(fachsem)
    studids.append(id)

print("(STATUS) : Student count", len(exportdata))


#### PROF DATA
with open(inputprofs) as input:
    profdata = json.load(input)

# define the data
profids=[]
profnames = []
profdatecnts = []
profdates = []
profweeks = []

# get data from json
idx=1
for key in profdata:
    prof = profdata[key]

    profdate = prof['termine']
    datecnt = prof['anztermine']
    weeks = []

    # get the calendar week for each date
    for datestring in profdate:
        isodate = date.fromisoformat(datestring.split(' ')[0])
        weeks.append(isodate.isocalendar()[1] - 47)

    print(weeks)

    # check if weeks are excluded and refine data
    for exclweek in EXCLUDE_WEEKS:
        if exclweek in weeks:
            i = weeks.index(exclweek)
            del profdate[i]
            datecnt -= 1
            del weeks[i]
            # print("(STATUS) : Prepare data ", prof['name'], "deleted date in week", exclweek)

    # check format
    assert datecnt == len(profdate) == len(weeks)

    profids.append(int(prof['prid']))
    profnames.append(prof['name'])

    profdatecnts.append(datecnt)
    profdates.append(profdate)
    profweeks.append(weeks)

    # just a check
    assert idx == int(prof['prid'])
    idx += 1


if ONLY_FIRST_WEEK:
    prof_capacities = [6 for dates in profdatecnts]
else:
    prof_capacities = [6*dates for dates in profdatecnts]
preferences = np.array(prefs)

assert len(prof_capacities) == len(preferences[0])

# solve the association problem
association = solve_meet_prof_optimization(bubble_capacities=prof_capacities, preferences=preferences)
association = np.array(association)

# contains all students, so that first every student gets one date, then a second
stud_heap = []

# how many students are associated to each prof
prof_stud_cnts = [0 for i in range(len(profids))]

# List for prof classes, to handle the group size and assignment
Professors = []

for prof_idx in range(len(profids)):
    assert prof_idx + 1 == profids[prof_idx]
    profstuds = np.nonzero(association[:, prof_idx])[0]
    prof_stud_cnts[prof_idx] = len(profstuds)
    Prof = Professor(stud_cnt=len(profstuds), student_lst=profstuds, name=profnames[prof_idx], optim_dates=False)
    Professors.append(Prof)


print("(INFO)  : Prof student counts", prof_stud_cnts)


if RAND_SORT:

    #### RANDOM SORTING
    for Prof in Professors:
        Prof.distributeRandom()

else:
    #### INTELLIGENT SORTING
    # get data from association matrix
    stud_idx = 0
    for studentasn in association:
        studprofs = np.nonzero(studentasn)[0]
        studid = studids[stud_idx]
        # print("ASN / profs / id", studentasn, studprofs[0], studid)

        heapq.heappush(stud_heap, (0, stud_idx, studid, tuple(studprofs), [-1, -1]))
        stud_idx += 1


    while stud_heap:
        visited, stud_idx, studid, studprofs, dates = heapq.heappop(stud_heap)

        if visited > 2:
            # added all possible students
            break

        success = False

        for i in range(len(studprofs)):
            if dates[i] == -1:
                Prof = Professors[studprofs[i]]
                if not Prof.full():
                    date = Prof.getDateForStudent(stud_idx)
                    dates[i] = date
                    heapq.heappush(stud_heap, (visited+1, stud_idx, studid, studprofs, dates))
                    success = True
                    break

        if not success:
            heapq.heappush(stud_heap, (visited + 1, stud_idx, studid, studprofs, dates))



#### IMPROVE DATES BY FILLING THEM UP


if OPTIMISE_DATES:
    incomplete_dates = []

    for prof_idx in range(len(Professors)):
        Prof = Professors[prof_idx]
        if not Prof.full():
            pending_date = Prof.dates[len(Prof.dates)-1]
            spots = 6 - len(pending_date)
            profdate = spots, prof_idx, Prof.name, pending_date
            incomplete_dates.append(profdate)

    incomplete_dates = sorted(incomplete_dates, key=lambda date_tuple: date_tuple[0])

    print("\n\n************************ OPTIM ***************************")
    print("(STATUS) : These dates must be optimised: ")
    for pd in incomplete_dates:
        print(pd)

    # this list contains students in wait list, in case they already are associated to the current Prof_add
    temporary_studs_on_hold = []
    fresh_prof = True

    while len(incomplete_dates) > 1:
        first = incomplete_dates[0]
        last = incomplete_dates[-1]

        # print("First ", first)
        # print ("Last ", last)

        Prof_add = Professors[first[1]]
        Prof_red = Professors[last[1]]

        if temporary_studs_on_hold and fresh_prof:
            stud_candidate = temporary_studs_on_hold.pop(0)

            if not Prof_add.studAlreadyMember(stud_candidate):
                Prof_add.getDateForStudent(stud_candidate)
            else:
                temporary_studs_on_hold.append(stud_candidate)
        else:
            stud_candidate = Prof_red.popStudent()

            if not Prof_add.studAlreadyMember(stud_candidate):
                Prof_add.getDateForStudent(stud_candidate)
            else:
                temporary_studs_on_hold.append(stud_candidate)

        fresh_prof = False

        # handle case of last prof -> its possible to get stuck here if temporary_studs_on_hold it not empty,
        # but the students are already added to the last prof of list.

        if Prof_red.full(prints=False):
            del incomplete_dates[-1]

        if Prof_add.full(prints=False):
            del incomplete_dates[0]
            # fresh prof -> studs on hold are handled first.
            fresh_prof = True

        # print(incomplete_dates)


#### READ OUT DATES FROM PROF CLASSES

membership = np.zeros((len(studids), len(profids)), dtype=np.int32)

prof_idx = 0
for Prof in Professors:
    date_idx = 0
    for date in Prof.dates:
        for stud_idx in date:
            membership[stud_idx][prof_idx] = profweeks[prof_idx][date_idx]
        date_idx += 1
    prof_idx += 1

#### SOME TESTS

for stud in membership:
    assert len(np.nonzero(stud)[0]) <= 2

    for pref in np.nonzero(stud)[0]:
        date = stud[pref]
        assert 4 >= date > 0

#### SOME STATS:

cnt_stud_w_two_dates = 0
cnt_stud_w_one_dates = 0
cnt_stud_w_no_dates = 0
cnt_full_dates = 0
cnt_nfull_dates = 0
cnt_empty_dates = 0
cnt_overflow_studs = 0

cnt_stud_w_two_full_dates = 0
cnt_stud_w_one_full_dates = 0
cnt_stud_w_no_full_dates = 0

studs_with_no_date = []
studs_with_one_date = []
studs_with_two_date = []

date_fill_count = [0 for i in range(7)]

for stud_idx in range(len(membership)):
    studdates = np.nonzero(membership[stud_idx])[0]
    if len(studdates) is 2:
        cnt_stud_w_two_dates += 1
    elif len(studdates) is 1:
        cnt_stud_w_one_dates += 1
    else:
        cnt_stud_w_no_dates += 1

    full_date = 0
    for prof in studdates:
        for date in Professors[prof].dates:
            if stud_idx in date and len(date) == 6:
                full_date += 1

    if full_date == 0:
        cnt_stud_w_no_full_dates += 1
        studs_with_no_date.append(stud_idx)
    elif full_date == 1:
        cnt_stud_w_one_full_dates += 1
        studs_with_one_date.append(stud_idx)
    else:
        cnt_stud_w_two_full_dates += 1
        studs_with_two_date.append(stud_idx)


empty_profs = []

for prof_idx in range(len(membership[0])):
    print()
    Professors[prof_idx].printMyDates()
    profdates = np.nonzero(membership[:, prof_idx])[0]
    # print(profdates, len(profdates))

    # basic check how many dates are full / empty / incomplete
    if len(profdates) is 0:
        cnt_empty_dates += 1
        empty_profs.append(Professors[prof_idx].name)
    elif len(profdates) % 6 is 0:
        cnt_full_dates += len(profdates) // 6
    elif not len(profdates) % 6 is 0:
        cnt_nfull_dates += 1
        cnt_overflow_studs += len(profdates) % 6
    else:
        pass

    # detailed check
    cnt_week_stud = [0 for i in range(4)]

    for stud in profdates:
        # print(stud, prof_idx)
        # print(membership[stud][prof_idx])
        cnt_week_stud[membership[stud][prof_idx]-1] += 1

    for datefill in cnt_week_stud:
        if datefill is not 0:
            date_fill_count[datefill] += 1

# calculate number of dates

datecount = 0
for d in date_fill_count:
    datecount += d

print("two date students: ", cnt_stud_w_two_dates)
print("one date students: ", cnt_stud_w_one_dates)
print("no date students: ", cnt_stud_w_no_dates)

print("two full date students: ", cnt_stud_w_two_full_dates)
print("one full date students: ", cnt_stud_w_one_full_dates)
print("no full date students: ", cnt_stud_w_no_full_dates)
print("studs with no full date:", studs_with_no_date)
print("studs with one full date:", studs_with_one_date)
print("studs with two full date:", studs_with_two_date)

print("\n---date stud stats---")
print("full dates: ", cnt_full_dates)
print("not full dates: ", cnt_nfull_dates)
print("empty dates: ", cnt_empty_dates)
print("overflow stud places: ", cnt_overflow_studs)


print("\n--- valid ---")
print("date fill states:", date_fill_count)


cnt_stud_got_their_prefs = [0 for i in range(3)]

for i in range(len(preferences)):
    prefs = preferences[i]
    # print(prefs)
    membs = membership[i]
    # print(membs)

    match = 0
    no_match = 0

    for p, m in zip(prefs, membs):
        if (p == 1 or p==3) and m > 0:
            match += 1
        elif m > 0:
            no_match += 1
        else:
            pass

    if match == 2 and no_match == 0:
        cnt_stud_got_their_prefs[2] += 1
    elif match == 1 and no_match == 1:
        cnt_stud_got_their_prefs[1] += 1
    elif match == 0 and no_match == 2:
        cnt_stud_got_their_prefs[0] += 1
    else:
        print("Something went wrong! Student ", i)
        print(match, no_match)
        print(membs)
        print(prefs)
        print("ID:", studids[i])
        print()

print("Student got so many of their preferences", cnt_stud_got_their_prefs)

stud_ids_no_full_date = [studids[i] for i in studs_with_no_date]
stud_ids_one_full_date = [studids[i] for i in studs_with_one_date]
stud_ids_two_full_dates = [studids[i] for i in studs_with_two_date]

stud_sem_no_full_date = [fachsems[i] for i in studs_with_no_date]
stud_sem_one_full_date = [fachsems[i] for i in studs_with_one_date]
stud_sem_two_full_dates = [fachsems[i] for i in studs_with_two_date]


print("Profs, that didnt get a date:")
print(empty_profs)


#### write stats to result

stats = dict(date_cnt=datecount,
             date_participant_cnts_comment="idx in list is date member count, value how many such dates exist",
             date_participant_cnts=date_fill_count,
             stud_result_pref_accordance_comment="prefs satisfied [none, one, two]",
             stud_result_pref_accordance=cnt_stud_got_their_prefs,
             stud_ids_two_full_dates=stud_ids_two_full_dates,
             stud_sem_two_full_dates=stud_sem_two_full_dates,
             stud_ids_one_full_date=stud_ids_one_full_date,
             stud_sem_one_full_date=stud_sem_one_full_date,
             stud_ids_no_full_date=stud_ids_no_full_date,
             stud_sem_no_full_date=stud_sem_no_full_date)

##### STORE RESULT AS DICT

result = dict()

result["stats"] = stats

for i in range(len(membership)):
    # print(membership[i], preferences[i])
    studdict = dict(id=studids[i], fachsem=fachsems[i], prefs=preferences[i].tolist(), dates=membership[i].tolist())
    result[str(i)] = studdict

with open('data/result6.json', 'w') as file:
    json.dump(result, file)
    file.close()


