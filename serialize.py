import datetime
import UpdateManager

start_date = datetime.datetime(2015,11,15)
P1 = (['EEM', 'UUP', 'GLD', 'NFLX'], [57, 134, 35, 4], [35.08, 26.11, 111.54, 117.22], 10000)
p = UpdateManager.start_manager_update_process(P1, start_date)
