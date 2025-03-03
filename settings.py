from dotenv import load_dotenv

import os

load_dotenv()

nj_doe_data_dir = os.path.abspath("./nj_doe/")

nj_doe_required_sheets = {
                            "Header and Contact": ["COUNTY_CODE", "DISTRICT_CODE", "SCHOOL_CODE", "COUNTY_NAME", "DISTRICT_NAME", "SCHOOL_NAME", "ADDRESS", "CITY_STATE_ZIP", "WEBSITE"], 
                            "EnrollmentTrendsbyGrade": ["CountyCode", "DistrictCode", "SchoolCode", "Grade06", "Grade07", "Grade08", "Grade09", "Grade10", "Grade11", "Grade12"], 
                            "EnrollmentTrendsByStudentGroup": ["CountyCode", "DistrictCode", "SchoolCode", "Economically Disadvantaged Students", "English Learners", "Female", "Homeless Students", "Male", "Migrant Students", "Military-Connected Students", "Students in Foster Care", "Students with Disabilities"], 
                            "EnrollmentByRacialEthnicGroup": ["CountyCode", "DistrictCode", "SchoolCode", "American Indian or Alaska Native", "Asian", "Black or African American", "Hispanic", "Native Hawaiian or Pacific Islander", "Two or More Races", "White"], 
                            "EnrollmentByHomeLanguage": ["CountyCode", "DistrictCode", "SchoolCode", "HomeLanguage", "%OfStudents"]
}

