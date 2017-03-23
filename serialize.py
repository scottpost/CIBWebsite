import datetime
import UpdateManager

start_date = datetime.datetime(2017,3,1)
portfolio_info = (['FCG', 'AMD', 'ADBE', 'DSKE', 'ACM'], [82, 87, 13, 119, 55], [24.57, 13.33, 119.92, 10.10, 37.52], 1082)
UpdateManager.start_manager_update_process(portfolio_info, start_date)
