from django.shortcuts import render
from django.http import HttpResponse
from src.apis.bgAPIs import bgScanSe, bgScanNl
from src.apis.overview import overview_func, size_overview
from functions import format_overview_se, format_overview_nl
from functions import milkdata_context, position_context, cowinfo_context
from functions import handle_uploaded_file, dutch_position_context, dutch_milkdata_context, dutch_cowinfo_context, sort_files_by_time, write_query_log, read_query_log, clear_query_log, query_log_isempty, download_log_file
from form import UploadFileForm
from cows.settings import BASE_DIR
from django.core.files.storage import FileSystemStorage
import os




def index(request):
   return render(request, "base.html",{})


def about(request):
   return render(request, 'about.html', {})

#def file_scan(request):
   #context = {}
   #if request.method == 'POST':
      #if 'pos' in request.POST:
         #context['pos'] = bgScanSe()
      #if 'info' in request.POST:
         #context['info'] = bgScanSe()

   #return render(request, 'file_scan.html', context)
def query_log(request):
   context = {}
   if request.method == 'POST':
      if request.POST['action'] == 'Clear Query Log':
         clear_query_log()
         context['msg'] = 'The log file has been cleared.'
      elif request.POST['action'] == 'Download Log File':
         return download_log_file()

   if query_log_isempty():
      context['msg'] = 'There are no logs to display, the file is empty.'
   else:
      context['msg'] = 'Contents of log file:'
   
   context['query_text_log'] = read_query_log()
   return render(request, 'query_log.html', context)

def download_after_query(request):
   from os import listdir
   from os.path import isfile, join

   context = {}
   files = [f for f in listdir('result_files') if isfile(join('result_files', f))]
   files = sort_files_by_time(files)
   context['file_names'] = files
   cleared_folder = False
   

   if request.method == 'POST':
      if request.POST['action'] == 'Clear files':
         for file in files:
            file = "result_files/"+file
            if os.path.exists(file):
               os.remove(file)
            else:
               pass
         context['file_names'] = []
         cleared_folder = True

      else:
         file_to_download = request.POST['action']
         path = 'result_files/'+file_to_download
         response = HttpResponse(open(path, 'rb').read())
         response['Content-Disposition'] = 'attachment; filename='+file_to_download
         response['Content-Type'] = 'text/plain'
         return response
      
   if cleared_folder:
      context['status_message'] = 'All files has been cleared from the "result_files" folder.'
   elif files == []:
      context['status_message'] ='Looks like there are no files in the "result_files" folder! To generate data files, go to:'
      context['data_link'] = True
   else:
      context['status_message'] =''

   return render(request, 'swe_data/download_after_query.html', context)


# ---- Upload to database views ----------
def upload_swedish(request):
   file_names = []
   context = {}
   form = UploadFileForm()
   size_sum = 0
   context['status'] = 'Waiting for user input.'
   if request.method == 'POST':
      try:
         form = UploadFileForm(request.POST, request.FILES)
         files = request.FILES.getlist('files')
         if form.is_valid():
            for f in files:
               handle_uploaded_file(f,'se/')
               file_names.append(f.name)
            context['file_names'] = file_names
            
            #Estimate size of files
            for f in files:
               size_sum = size_sum + f.size

            #upload to swe database here
            bgScanSe() # Scan for swedish files to upload
            context['size_sum'] = 'Total size of files: {} MB'.format(size_sum/1000000)
            context['msg'] = 'File(s) submitted. The file will be visible in the Overview tab when it is successfully uploaded (for position data, this may take a while).'
            context['file_text'] = 'File(s) submitted:'
            context['status'] = 'Success!'
            
      except Exception as error:
         form = UploadFileForm()
         print('Error occured in upload_swe:')
         print(error)
         context['status'] = 'Error occured! The following message was past: "{}".'.format(error)
      finally:
         return render(request, 'upload/upload_swedish.html', context)
   return render(request, 'upload/upload_swedish.html', context)


def upload_dutch(request):
   file_names = []
   context = {}
   form = UploadFileForm()
   size_sum = 0
   context['status'] = 'Waiting for user input.'
   if request.method == 'POST':
      try:
         form = UploadFileForm(request.POST, request.FILES)
         files = request.FILES.getlist('files')

         if form.is_valid():
            for f in files:
               handle_uploaded_file(f,'nl/')
               file_names.append(f.name)
            context['file_names'] = file_names

         #Estimate size of files
         for f in files:
            size_sum = size_sum + f.size

         bgScanNl() # Scan for swedish files to upload
         #upload to dutch database here
         context['size_sum'] = 'Total size of files: {} MB'.format(size_sum/1000000)
         context['msg'] = 'The following files have been passed to the database:'
         context['status'] = 'Success!'
      except Exception as error:
         form = UploadFileForm()
         print('Error occured in upload_dutch:')
         print(error)
         context['status'] = 'Error occured! The following message was past: "{}".'.format(error)
         
      
      finally:
         return render(request, 'upload/upload_dutch.html', context)
   return render(request, 'upload/upload_dutch.html', context)
# [['hej','hej','hej','hej'],['hej','hej','hej','hej'],['hej','hej','hej','hej'],['hej','hej','hej','hej'],['hej','hej','hej','hej'],['hej','hej','hej','hej'],['hej','hej','hej','hej']]
def overview(request):
   context = {}
   try:
      over = overview_func()
      list_info_se, list_pos_se = format_overview_se(over[0])
      list_info_nl, list_pos_nl = format_overview_nl(over[1])
      list_size = size_overview()
      context = {
         'info_header': ['KO','Health','Avkastn','Milk'],
         'position_header': ['FA','PA','PAA','PC'],
         'size_header': ['Table name', 'Nr of Records', 'Size (MB)'],
         'list_pos': list_pos_se,
         'list_info': list_info_se,
         'list_size': list_size[0],
         'dutch_info_header': ['File'],
         'dutch_position_header': ['FA','PA','PAA','PC'],
         'dutch_size_header': ['Table name', 'Nr of Records', 'Size (MB)'],
         'dutch_list_pos': list_pos_nl,
         'dutch_list_info': list_info_nl,
         'dutch_list_size': list_size[1],
      }
      context['status_message'] = 'Successfully connected to the database.'
   except Exception as error:
      print('Error: ')
      print(error)
      context = {
         'info_header': ['KO','Health','Avkastn','Milk'],
         'position_header': ['FA','PA','PAA','PC'],
         'size_header': ['Table name', 'Nr of Records', 'Size (MB)'],
         'list_pos': [],
         'list_info': [],
         'list_size': [],
         'dutch_info_header': ['File'],
         'dutch_position_header': ['FA','PA','PAA','PC'],
         'dutch_size_header': ['Table name', 'Nr of Records', 'Size (MB)'],
         'dutch_list_pos': [],
         'dutch_list_info': [],
         'dutch_list_size': [],
      }
      context['status_message'] = 'Failed to connect to database, the following error message were passed: ' + str(error)
   finally:
      return render(request, "overview.html", context)




# --------- SWEDISH DATABASE ------------ #
def swe_db(request):  
   return render(request, "swe_data/swe_db.html",{})


def swe_position(request):
   context = {}
   context['status_message'] = 'Waiting for user input.'



   if request.method == 'POST':


      if request.POST['action'] == 'query':
         context, query_successful = position_context(request)
         if query_successful == True:
            try:
               if context['cow_id'] == '':
                  cow_id = []
               else:
                  cow_id = list(map(int, context['cow_id'].split(',')))
               if context['group_nr'] == '':
                  grp = []
               else:
                  grp = list(map(int, context['group_nr'].split(',')))
               if context['tag_str'] == '':
                  tag_strs = []
               else:
                  tag_strs = list(map(str, context['tag_str'].replace(' ', '').split(',')))

               stats = context['status_list']
               types = context['position_list']
               start_date = context['start_date']
               end_date = context['end_date']
               start_time = context['start_time']
               end_time = context['end_time']
               periodic = context['periodic']

               from src.apis.query_se import positionQuery
               files = positionQuery(cow_id, grp, stats, types, tag_strs, start_date, end_date, start_time, end_time, periodic)
               #iles = ['1','2','3']
               files = list(map(lambda x: x[0], files))
               files = ' '.join(files)

               write_query_log('Swedish Position Data Query',context['user_inputs'],files)
               context['download_link'] = True
               context['status_message'] = 'Query was successful, following files have been generated and can be found in '\
                  'result_files/{}'.format(files)
            except Exception as error:
                  print('Error: ')
                  print(error)
                  context['status_message'] = 'Failed to query, the following error message were passed: ' + str(error)
            finally:
               return render(request, "swe_data/swe_position.html", context)
         else:
            context['status_message'] = 'Mandatory input fields are missing, please try again.'
            return render(request, "swe_data/swe_position.html", context)
   
   else:
      return render(request, "swe_data/swe_position.html", context)


def swe_milkdata(request):
   context = {}
   context['status_message'] = 'Waiting for user input.'
   if request.method == 'POST':
      context, query_successful = milkdata_context(request)
      if query_successful == True:
         try:
            if context['cow_id'] == '':
               cow_id = []
            else:
               cow_id = list(map(int, context['cow_id'].split(',')))
            if context['group_nr'] == '':
               grp = []
            else:
               grp = list(map(int, context['group_nr'].split(',')))

            
            stats = context['status_list']
            start_date = context['start_date']
            end_date = context['end_date']
            output_list = context['output_list']
            from src.apis.query_se import milkQuery
            #return_info = milkQuery(cow_id, grp, stats, start_date, end_date, output_list)
            files = milkQuery(cow_id, grp, stats, start_date, end_date, output_list)
            #files = ['4311','212','331']
            files = list(map(lambda x: x[0], files))
            files = ' '.join(files)
            write_query_log('Swedish MilkData Query',context['user_inputs'],files)
            context['download_link'] = True
            context['status_message'] = 'Query was successful, file has been generated.'
         except Exception as error:
            print('Error: ')
            print(error)
            context['status_message'] = 'Failed to query, the following error message were passed: ' + str(error)
         finally:
            return render(request, "swe_data/swe_milkdata.html", context)
      else:
         context['status_message'] = 'Mandatory input fields are missing, please try again.'
         return render(request, "swe_data/swe_milkdata.html", context)
   else:
      return render(request, "swe_data/swe_milkdata.html", context)


def swe_cowinfo(request):
   context = {}
   context['status_message'] = 'Waiting for user input.'
   if request.method == 'POST':
      context, query_successful = cowinfo_context(request)
      if query_successful == True:
         try:
            if context['cow_id'] == '':
               cow_id = []
            else:
               cow_id = list(map(int, context['cow_id'].split(',')))
            if context['group_nr'] == '':
               grp = []
            else:
               grp = list(map(int, context['group_nr'].split(',')))
            stats = context['STATUS']
            start_date = context['start_date']
            end_date = context['end_date']
            fields = context['output_list']
            type = int(context['special_field'])

            from src.apis.query_se import infoQuery
            files = infoQuery(cow_id, grp, stats, start_date, end_date, fields, type)
            files = list(map(lambda x: x[0], files))
            files = list(filter(lambda x: x, files))
            files = ' '.join(files)
            write_query_log('Swedish Cow Data Query',context['user_inputs'],files)
            
            context['download_link'] = True
            context['status_message'] = 'Query was successful, following files have been generated and can be found in'\
               ' result_files/ with names of {}'.format(files)
         except Exception as error:
            print('Error: ')
            print(error)
            context['status_message'] = 'Failed to query, the following error message were passed: ' + str(error)
         finally:
            return render(request, "swe_data/swe_cowinfo.html", context)
      else:
         context['status_message'] = 'Mandatory input fields are missing, please try again.'
         return render(request, "swe_data/swe_cowinfo.html", context)

   else:
      return render(request, "swe_data/swe_cowinfo.html", context)



def swe_mapping_info(request):
   context = {}
   context['status'] = 'Waiting for user to input Cow ID.'

   if request.method == 'POST':
      cow_id = request.POST['cow_id']
      if cow_id == '':
         context['msg'] = 'Cow ID is required to render table, try again!'
      else:
         try:
            cow_id = int(cow_id)
         except:
            context['msg'] = 'Incorrect format, Cow ID must be an integer! Your input:'
            context['msg_id'] = '{}'.format(cow_id)
            return render(request,'swe_data/swe_mapping_info.html', context)
         try:
            from src.apis.query_se import refQuery
            context['map_LoL'] = refQuery(cow_id)
        
            if not any(context['map_LoL']):
               context['status'] = 'Failed'
               context['msg'] = 'No mapping info exists for cow id = {}.'.format(cow_id)
            else:
               context['msg'] = 'Mapping info found!'
               context['map_header'] = ['Tag Nr', 'Start date', 'End date']
               context['status'] = 'Success!'
               context['msg'] = 'Mapping info found!'
               context['msg_id'] = 'Rendering table using cow id = {}.'.format(cow_id)
         except Exception as error:
            context['status'] = 'Something went wrong!'
            context['msg'] = 'Error occured: {}'.format(error)
         finally:
            return render(request,'swe_data/swe_mapping_info.html', context)

   return render(request,'swe_data/swe_mapping_info.html', context)


# -------- DUTCH DATABASE ------------- #
def dutch_data(request):
   return render(request, "dutch_data/dutch_select.html",{})


def dutch_position(request):
   if request.method == 'POST':
      context, query_successful = dutch_position_context(request)
      if query_successful:
         try:
            tag_strs = list(filter(lambda x: x != "", map(str, context['tag_str'].replace(' ', '').split(','))))

            types = context['position_list']
            start_date = context['start_date']
            end_date = context['end_date']
            start_time = context['start_time']
            end_time = context['end_time']
            periodic = context['periodic']
      
            
            #query function call
            from src.apis.query_nl import positionQuery
            files = positionQuery([], tag_strs, types, start_date, end_date, start_time, end_time, periodic) 
            files = list(map(lambda x: x[0], files))
            files = list(filter(lambda x: x, files))
            files = ' '.join(files)
            write_query_log('Dutch Position Query',context['user_inputs'],files)

            context['download_link'] = True
            context['status_message'] = 'Query was successful, following files have been generated and can be found in'\
               ' result_files/ with names of {}'.format(files)
         except Exception as error:
               print('Error: ')
               print(error)
               context['status_message'] = 'Failed to query, the following error message were passed: ' + str(error)
         finally:
            return render(request, "dutch_data/dutch_position.html", context)
      else:
         context['status_message'] = 'Mandatory input fields are missing, please try again.'
         return render(request, "dutch_data/dutch_position.html", context)
   
   else:
      return render(request, "dutch_data/dutch_position.html", {})
   return render(request, "dutch_data/dutch_position.html", {})




def dutch_milkdata(request):

   if request.method == 'POST':
      context, query_successful = dutch_milkdata_context(request)
      if query_successful == True:
         try:
            if context['cow_id'] == '':
               cow_id = []
            else:
               cow_id = list(map(int, context['cow_id'].split(',')))
            start_date = context['start_date']
            end_date = context['end_date']
            
            
            from src.apis.query_nl import milkQuery
            files = milkQuery(cow_id, start_date, end_date)
            files = list(map(lambda x: x[0], files))
            files = list(filter(lambda x: x, files))
            files = ' '.join(files)
            write_query_log('Dutch Milk Data Query',context['user_inputs'],files)
            context['download_link'] = True
            context['status_message'] = 'Query was successful, following files have been generated and can be found in'\
               ' result_files/ with names of {}'.format(files)
         except Exception as error:
            print('Error: ')
            print(error)
            context['status_message'] = 'Failed to query, the following error message were passed: ' + str(error)
         finally:
            return render(request,"dutch_data/dutch_milkdata.html", context)
      else:
         context['status_message'] = 'Mandatory input fields are missing, please try again.'
         return render(request, "dutch_data/dutch_milkdata.html", context)
   else:
      return render(request, "dutch_data/dutch_milkdata.html", {})



def dutch_mapping_info(request):
   context = {}
   context['status'] = 'Waiting for user to input Cow ID.'

   if request.method == 'POST':
      cow_id = request.POST['cow_id']
      if cow_id == '':
         context['msg'] = 'Cow ID is required to render table, try again!'
      else:
         try:
            cow_id = int(cow_id)
         except:
            context['msg'] = 'Incorrect format, Cow ID must be an integer! Your input:'
            context['msg_id'] = '{}'.format(cow_id)
            return render(request,'dutch_data/dutch_mapping_info.html', context)
         try:
            #context['map_LoL'] = [['tag1','date1','date1'],['tag2','date2','date2'],['tag3','date3','date3']] #test data
            context['map_header'] = ['Tag Nr', 'Start date', 'End date']
            context['status'] = 'Success!'
            context['msg'] = 'Mapping info found!'
            context['msg_id'] = 'Rendering table using cow id = {}.'.format(cow_id)
      
            from src.apis.query_nl import refQuery
            refQuery(cow_id)
         except Exception as error:
            context['status'] = 'Something went wrong!'
            context['msg'] = 'Error occured: {}'.format(error)
         finally:
            return render(request,'dutch_data/dutch_mapping_info.html', context)

   return render(request,'dutch_data/dutch_mapping_info.html', context)

def dutch_cowinfo(request): # Not in use
 
   if request.method == 'POST':
      context, query_successful = dutch_cowinfo_context(request)
      if query_successful == True:
         try:
            if context['cow_id'] == '':
               cow_id = []
            else:
               cow_id = list(map(int, context['cow_id'].split(',')))
            
            stats = context['STATUS']
            start_date = context['start_date']
            end_date = context['end_date']
            fields = context['output_list']
            insem_type = context['insem_type']
            
            # query function
            context['status_message'] = 'Query was successful, file has been generated.'
         except Exception as error:
            print('Error: ')
            print(error)
            context['status_message'] = 'Failed to query, the following error message were passed: ' + str(error)
         finally:
            return render(request, "dutch_data/dutch_cowinfo.html", context)
      else:
         context['status_message'] = 'Mandatory input fields are missing, please try again.'
         return render(request, "dutch_data/dutch_cowinfo.html", context)

   else:
      return render(request, "dutch_data/dutch_cowinfo.html", {})


