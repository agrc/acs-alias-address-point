acs-alias-address-point
=======================

Assign ACS alias street values to address point data.

- Tool usage
	
	- Provide a path to the address point data, road data and output directory
	- Tool will produce a geodatabase in output directory that contains the address points with alias fields added
	
- Notes
	-Large data sets can take a long time to run
	
- Pseudo code
   
   -For each unique road name (Prefix + street + street type)
   		-Select all address points with the road name.
   		-Select all roads with the road name.
   		-Find the road from the selected set that is closest to each point.
   		-To each address point add the alias fields from the closest road to that point. 

