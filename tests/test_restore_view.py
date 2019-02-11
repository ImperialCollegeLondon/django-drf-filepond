import logging

from django.test.testcases import TestCase

LOG = logging.getLogger(__name__)

#########################################################################
# The restore endpoint is used by the client to load a remote temporary   
# file from the server. 
# https://pqina.nl/filepond/docs/patterns/api/server/#restore
# The filepond client makes a restore request to the server which looks 
# up the provided file upload ID in the TemporaryUpload table and then   
# returns the file to the client if a valid upload ID was provided.
# 
# test_restore_incorrect_method: Make POST/PUT/DELETE requests to the restore  
#     endpoint to check that these are rejected with 405 method not allowed
#
# test_restore_blank_id: Make a GET request to the restore endpoint with  
#     a blank ID provided in the URL query string. 
#
# test_restore_invalid_id: Make a GET request to the restore endpoint with    
#     an invalid ID provided in the URL query string.
#
# test_restore_id_notfound_error: Make a GET request to the restore endpoint    
#     with an ID that is a valid format but for which no record exists (404).
#
# test_restore_file_notfound_error: Make a GET request to the restore     
#     endpoint with a valid ID but for which the file doesn't exist (404).
#
# test_restore_file_read_error: Make a GET request to the restore endpoint    
#     where an occurs when trying to read the target file (500) 
#
# test_restore_successful_request: Make a GET request to the restore endpoint  
#     that is successful. 
#
class RestoreTestCase(TestCase):

    def test_restore_incorrect_method(self):
        pass  

    def test_restore_blank_id(self):
        pass   

    def test_restore_invalid_id(self):
        pass    

    def test_restore_id_notfound_error(self):
        pass    

    def test_restore_file_notfound_error(self):
        pass     

    def test_restore_file_read_error(self):
        pass    

    def test_restore_successful_request(self):
        pass  
