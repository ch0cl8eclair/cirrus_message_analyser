 .PHONY install-requirements update-driver
 
 install-requirements:
      pip install -Ur ./app/requirements.txt
      
update-driver:
      . ./app/update-driver.sh
