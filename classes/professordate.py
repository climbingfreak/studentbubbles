from random import randint, shuffle
import queue
import numpy as np

class Professor:

    def __init__(self, stud_cnt, student_lst=None, optim_dates=True, date_count=4, name="default"):

        self.name = name

        if student_lst is not None:
            assert stud_cnt == len(student_lst)


        if isinstance(student_lst, np.ndarray):
            self.students = student_lst.tolist()
        else:
            self.students = student_lst
        self.student_cnt = stud_cnt

        self.max_date_members = 6
        self.min_date_members = 0
        self.added_students = 0

        if optim_dates:
            if self.student_cnt < self.min_date_members:
                print("(ERROR) [", self.name, "]: less then ", self.min_date_members, " students for prof.")
            elif self.student_cnt <= 6:
                self.max_date_members = 6
                self.date_cnt = 1
            elif self.student_cnt <= 9:
                self.max_date_members = 5
                self.date_cnt = 2
            elif self.student_cnt <= 12:
                self.max_date_members = 6
                self.date_cnt = 2
            elif self.student_cnt <= 15:
                self.max_date_members = 5
                self.date_cnt = 3
            elif self.student_cnt <= 18:
                self.max_date_members = 6
                self.date_cnt = 3
            elif self.student_cnt <= 20:
                self.max_date_members = 5
                self.date_cnt = 4
            elif self.student_cnt <= 24:
                self.max_date_members = 6
                self.date_cnt = 4

        else:
            self.date_cnt = stud_cnt // 6
            if stud_cnt % 6 is not 0:
                self.date_cnt += 1
            print("(STATUS) [", self.name, "]: Students ", self.student_cnt, " dates ", self.date_cnt)


        self.dates = [[] for i in range(self.date_cnt)]



    def distributeRandom(self):

        assert self.students is not None

        shuffle(self.students)
        stud_q = queue.Queue()

        # fill queue
        for stud in self.students:
            stud_q.put(stud)

        # fill dates
        for i in range(self.date_cnt):
                while not stud_q.empty() and len(self.dates[i]) < self.max_date_members:
                    self.dates[i].append(stud_q.get())
                    self.added_students += 1

        if self.student_cnt is not 0 and not self.full():
            print("(STATUS) [", self.name, "]:", self.dates)

        return self.dates

    def studAlreadyMember(self, stud):
        return stud in self.students

    def getDateForStudent(self, stud):
        group = self.testDateForStudent(stud)
        self.added_students += 1
        self.dates[group].append(stud) # add to group
        self.students.append(stud)
        return group

    def testDateForStudent(self, stud):
        group = self.added_students // self.max_date_members
        # print("[", self.name, "] stud: ", stud, "group: ", group)
        assert group <= self.date_cnt
        return group

    def full(self, prints=False):
        full = (not (self.added_students < self.date_cnt * self.max_date_members))
        if full:
            if prints:
                print("[", self.name, "] I am full. Student count ", self.added_students)
        return full

    def getRandIdx(self):
        return randint(0, len(self.students)-1)

    def printMyDates(self):
        print("[", self.name, "] ", self.dates)

    def popStudent(self):
        student = self.dates[-1][-1]
        del self.dates[-1][-1]
        self.added_students -= 1
        print("[", self.name, "] student removed: ", student)
        if len(self.dates[-1]) == 0:
            del self.dates[-1]
            self.date_cnt -= 1
        return student


class Student:
    pass




if __name__ == "__main__":
    student_list = [1,2,3,4,5,6,7,8,9,10,11]

    print("len ", len(student_list))
    Prof = Professor(len(student_list), student_list)
    dates = Prof.distributeRandom()

    print(dates)


    for i in student_list:
        Prof.getDateForStudent(i)