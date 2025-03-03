from dotenv import load_dotenv

import os

load_dotenv()

nj_doe_data_dir = os.path.abspath("./nj_doe/")

nj_doe_required_sheets = {
                            "Header and Contact": {"input": ["COUNTY_CODE", "DISTRICT_CODE", "SCHOOL_CODE", "COUNTY_NAME", "DISTRICT_NAME", "SCHOOL_NAME", "ADDRESS", "CITY_STATE_ZIP"],
                                                   "output": ["county_code", "district_code", "school_code", "county_name", "district_name", "school_name", "address", "city_state_zip"]}, 
                            "EnrollmentTrendsbyGrade": {"input": ["CountyCode", "DistrictCode", "SchoolCode", "Grade06", "Grade07", "Grade08", "Grade09", "Grade10", "Grade11", "Grade12"],
                                                        "output": ["county_code", "district_code", "school_code", "grade06", "grade07", "grade08", "grade09", "grade10", "grade11", "grade12"]}, 
                            "EnrollmentTrendsByStudentGroup": {"input": ["CountyCode", "DistrictCode", "SchoolCode", "Economically Disadvantaged Students", "English Learners", "Female", "Homeless Students", "Male", "Migrant Students", "Military-Connected Students", "Students in Foster Care", "Students with Disabilities"],
                                                               "output": ["county_code", "district_code", "school_code", "economically_disadvantaged", "english_learners", "female", "homeless", "male", "migrant", "military_connected", "in_foster_care", "with_disabilities"]}, 
                            "EnrollmentByRacialEthnicGroup": {"input": ["CountyCode", "DistrictCode", "SchoolCode", "American Indian or Alaska Native", "Asian", "Black or African American", "Hispanic", "Native Hawaiian or Pacific Islander", "Two or More Races", "White"],
                                                              "output": ["county_code", "district_code", "school_code", "american_indian_or_alaska_native", "asian", "black_or_african_american", "hispanic", "native_hawaiian_or_pacific_islander", "two_or_more_races", "white"]}, 
                            "EnrollmentByHomeLanguage": {"input": ["CountyCode", "DistrictCode", "SchoolCode", "HomeLanguage", "%OfStudents"],
                                                         "output": ["county_code", "district_code", "school_code", "home_language", "pct_of_students"]}
}

