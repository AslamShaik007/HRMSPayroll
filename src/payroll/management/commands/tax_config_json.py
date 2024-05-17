#this file is used to config the state wise default taxes when the new setup is done.

state_taxes_dict={
  "Andhra Pradesh": {
    "base":"monthly",
    "male":{
        "salary_ranges":["0-15000","15000-20000","20000-x"],
        "tax_value":[0,150,200]
    },
    "female":{
        "salary_ranges":["0-15000","15000-20000","20000-x"],
        "tax_value":[0,150,200]
    },
    "exception":{
        "month":[],
        "value":[]
    }  
},
  "Arunachal Pradesh": {
    "base":"monthly",
    "male":{
        "salary_ranges":["0-15000","15000-20000","20000-x"],
        "tax_value":[0,150,200]
    },
    "female":{
        "salary_ranges":["0-15000","15000-20000","20000-x"],
        "tax_value":[0,150,200]
    },
    "exception":{
        "month":[],
        "value":[]
    }  
},
  "Assam": {
    "base": "monthly",
    "male": {
      "salary_ranges": ["0-10000", "10001-15000", "15001-25000", "25001-x"],
      "tax_value": [0, 150, 180, 208]
    },
    "female": {
      "salary_ranges": ["0-10000", "10001-15000", "15001-25000", "25001-x"],
      "tax_value": [0, 150, 180, 208]
    },
    "exception": {
      "month": [],
      "value": []
    }
  },
  "Bihar": {
    "base": "monthly",
    "male": {
      "salary_ranges": ["0-25000", "25001-41666", "41667-83333", "83334-x"],
      "tax_value": [0, 83.33, 166.66, 208.33]
    },
    "female": {
      "salary_ranges": ["0-25000", "25001-41666", "41667-83333", "83334-x"],
      "tax_value": [0, 83.33, 166.66, 208.33]
    },
    "exception": {
      "month": [],
      "value": []
    }
  },
  "Chhattisgarh": {
    "base": "monthly",
    "male": {
      "salary_ranges": ["0-3333", "3333-4166", "4166-5000", "5000-6666", "6666-8333", "8333-12500", "12500-16666", "16666-20833", "20833-25000", "25000-x"],
      "tax_value": [0, 30, 60, 90, 100, 120, 150, 180, 190, 200]
    },
    "female": {
      "salary_ranges": ["0-3333", "3333-4166", "4166-5000", "5000-6666", "6666-8333", "8333-12500", "12500-16666", "16666-20833", "20833-25000", "25000-x"],
      "tax_value": [0, 30, 60, 90, 100, 120, 150, 180, 190, 200]
    },
    "exception": {
      "month": [],
      "value": []
    }
  },
  "NCT of Delhi": {
    "base": "monthly",
    "male": {
      "salary_ranges": ["0-50000", "50001-75000", "75001-100000", "100000-x"],
      "tax_value": [0, 100, 150, 200]
    },
    "female": {
      "salary_ranges": ["0-50000", "50001-75000", "75001-100000", "100000-x"],
      "tax_value": [0, 100, 150, 200]
    },
    "exception": {
      "month": [],
      "value": []
    }
  },
  "Goa": {
    "base": "monthly",
    "male": {
      "salary_ranges": ["0-7500", "7501-10000", "10000-x"],
      "tax_value": [0, 175, 200]
    },
    "female": {
      "salary_ranges": ["0-7500", "7501-10000", "10000-x"],
      "tax_value": [0, 175, 200]
    },
    "exception": {
      "month": ["2"],
      "value": [300]
    }
  },
  "Gujarat": {
    "base": "monthly",
    "male": {
      "salary_ranges": ["0-12000", "12000-x"],
      "tax_value": [0, 200]
    },
    "female": {
      "salary_ranges": ["0-12000", "12000-x"],
      "tax_value": [0, 200]
    },
    "exception": {
      "month": [],
      "value": []
    }
  },
  "Himachal Pradesh": {
    "base": "monthly",
    "male": {
      "salary_ranges": ["0-7500", "7501-10000", "10000-x"],
      "tax_value": [0, 175, 200]
    },
    "female": {
      "salary_ranges": ["0-7500", "7501-10000", "10000-x"],
      "tax_value": [0, 175, 200]
    },
    "exception": {
      "month": ["2"],
      "value": [300]
    }
  },
  "Haryana": {
    "base": "monthly",
    "male": {
      "salary_ranges": ["0-7500", "7501-10000", "10000-x"],
      "tax_value": [0, 175, 200]
    },
    "female": {
      "salary_ranges": ["0-7500", "7501-10000", "10000-x"],
      "tax_value": [0, 175, 200]
    },
    "exception": {
      "month": ["2"],
      "value": [300]
    }
  },
  "Jharkhand": {
    "base": "monthly",
    "male": {
      "salary_ranges": ["0-25000", "25001-41666", "41667-66666", "66667-83333", "83334-x"],
      "tax_value": [0, 100, 150, 175, 208]
    },
    "female": {
      "salary_ranges": ["0-25000", "25001-41666", "41667-66666", "66667-83333", "83334-x"],
      "tax_value": [0, 100, 150, 175, 208]
    },
    "exception": {
      "month": [],
      "value": []
    }
  },
  "Karnataka": {
    "base": "monthly",
    "male": {
      "salary_ranges": ["1-9999", "10000-14999", "15000-x"],
      "tax_value": [0, 0, 200]
    },
    "female": {
      "salary_ranges": ["1-9999", "10000-14999", "15000-x"],
      "tax_value": [0, 0, 200]
    },
    "exception": {
      "month": [],
      "value": []
    }
  },
  "Kerala": {
    "base": "monthly",
    "male": {
      "salary_ranges": ["0-1999", "2000-2999", "3000-4999", "5000-7499", "7500-9999", "10000-12499", "12500-16666", "16667-20833", "20833-x"],
      "tax_value": [0, 20, 30, 50, 75, 100, 125, 166, 208]
    },
    "female": {
      "salary_ranges": ["0-1999", "2000-2999", "3000-4999", "5000-7499", "7500-9999", "10000-12499", "12500-16666", "16667-20833", "20833-x"],
      "tax_value": [0, 20, 30, 50, 75, 100, 125, 166, 208]
    },
    "exception": {
      "month": [],
      "value": []
    }
  },
  "Madhya Pradesh": {
    "base": "monthly",
    "male": {
      "salary_ranges": ["0-18750", "18751-25000", "25001-33333", "33334-x"],
      "tax_value": [0, 125, 167, 208]
    },
    "female": {
      "salary_ranges": ["0-18750", "18751-25000", "25001-33333", "33334-x"],
      "tax_value": [0, 125, 167, 208]
    },
    "exception": {
      "month": [],
      "value": []
    }
  },
  "Maharashtra": {
    "base":"monthly",
    "male":{
        "salary_ranges":["0-7500","7501-10000","10001-x"],
        "tax_value":[0,175,200]
    },
    "female":{
        "salary_ranges":["0-7500","7501-10000","10001-x"],
        "tax_value":[0,0,175]
    },
    "exception":{
        "month":["2"],
        "value":[300]
    }  
},
  "Manipur": {
    "base": "monthly",
    "male": {
      "salary_ranges": ["0-4166", "4167-6250", "6251-8333", "8333-10416", "10417-x"],
      "tax_value": [0, 100, 166, 200, 208]
    },
    "female": {
      "salary_ranges": ["0-4166", "4167-6250", "6251-8333", "8333-10416", "10417-x"],
      "tax_value": [0, 100, 166, 200, 208]
    },
    "exception": {
      "month": [],
      "value": []
    }
  },
  "Meghalaya": {
    "base":"monthly",
    "male":{
        "salary_ranges":["0-4166","4167-6250","6251-8333","8333-12500","12501-16666","16667-20833","20834-25000","25001-29166","29167-33333","33334-37500","37500-41666","41667-x"],
        "tax_value":[0,16,25,41,62,83,104,125,150,175,200,208]
    },
    "female":{
        "salary_ranges":["0-4166","4167-6250","6251-8333","8333-12500","12501-16666","16667-20833","20834-25000","25001-29166","29167-33333","33334-37500","37500-41666","41667-x"],
        "tax_value":[0,16,25,41,62,83,104,125,150,175,200,208]
    },
    "exception":{
        "month":[],
        "value":[]
    }  
},
  "Mizoram": {
    "base":"monthly",
    "male":{
        "salary_ranges":["0-5000","5001-8000","8001-10000","10001-12000","12001-15000","15000-x"],
        "tax_value":[0,75,120,150,180,208]
    },
    "female":{
        "salary_ranges":["0-5000","5001-8000","8001-10000","10001-12000","12001-15000","15000-x"],
        "tax_value":[0,75,120,150,180,208]
    },
    "exception":{
        "month":[],
        "value":[]
    }  
},
  "Nagaland": {
    "base":"monthly",
    "male":{
        "salary_ranges":["0-4000","4001-5000","5001-7000","7001-9000","9001-12000","12000-x"],
        "tax_value":[0,35,75,110,180,208]
    },
    "female":{
        "salary_ranges":["0-4000","4001-5000","5001-7000","7001-9000","9001-12000","12000-x"],
        "tax_value":[0,35,75,110,180,208]
    },
    "exception":{
        "month":[],
        "value":[]
    }  
},
  "Odisha": {
    "base":"monthly",
    "male":{
        "salary_ranges":["0-13304","13305-25000","25001-x"],
        "tax_value":[0,125,200]
    },
    "female":{
        "salary_ranges":["0-13304","13305-25000","25001-x"],
        "tax_value":[0,125,200]
    },
    "exception":{
        "month":["2"],
        "value":[300]
    }  
},
  "Punjab": {
    "base":"monthly",
    "male":{
        "salary_ranges":["0-7500","7501-10000","10000-x"],
        "tax_value":[0,175,200]
    },
    "female":{
        "salary_ranges":["0-7500","7501-10000","10000-x"],
        "tax_value":[0,175,200]
    },
    "exception":{
        "month":["2"],
        "value":[300]
    }  
},
  "Rajasthan": {
    "base":"monthly",
    "male":{
        "salary_ranges":["0-7500","7501-10000","10000-x"],
        "tax_value":[0,175,200]
    },
    "female":{
        "salary_ranges":["0-7500","7501-10000","10000-x"],
        "tax_value":[0,175,200]
    },
    "exception":{
        "month":["2"],
        "value":[300]
    }  
},
  "Sikkim": {
    "base":"monthly",
    "male":{
        "salary_ranges":["0-1666","1667-2500","25001-33333","33334-x"],
        "tax_value":[0,125,150,200]
    },
    "female":{
        "salary_ranges":["0-1666","1667-2500","25001-33333","33334-x"],
        "tax_value":[0,125,150,200]
    },
    "exception":{
        "month":[],
        "value":[]
    }  
},
  "Tamil Nadu": {
    "base":"monthly",
    "male":{
        "salary_ranges":["0-21000","21000-30000","30001-45000","45001-60000","60001-75000","75000-x"],
        "tax_value":[0,130,315,690,1025,1250]
    },
    "female":{
        "salary_ranges":["0-21000","21000-30000","30001-45000","45001-60000","60001-75000","75000-x"],
        "tax_value":[0,130,315,690,1025,1250]
    },
    "exception":{
        "month":[],
        "value":[]
    }  
},
  "Telangana": {
    "base":"monthly",
    "male":{
        "salary_ranges":["0-15000","15000-20000","20000-x"],
        "tax_value":[0,150,200]
    },
    "female":{
        "salary_ranges":["0-15000","15000-20000","20000-x"],
        "tax_value":[0,150,200]
    },
    "exception":{
        "month":[],
        "value":[]
    }  
},
  "Tripura": {
    "base":"monthly",
    "male":{
        "salary_ranges":["0-7500","7501-15000","15000-x"],
        "tax_value":[0,150,208]
    },
    "female":{
        "salary_ranges":["0-7500","7501-15000","15000-x"],
        "tax_value":[0,150,208]
    },
    "exception":{
        "month":[],
        "value":[]
    }  
},
  "Uttar Pradesh": {
    "base":"monthly",
    "male":{
        "salary_ranges":["0-x"],
        "tax_value":[208.33]
    },
    "female":{
        "salary_ranges":["0-x"],
        "tax_value":[208.33]
    },
    "exception":{
        "month":[],
        "value":[]
    }  
},
  "Uttarakhand": {
    "base":"monthly",
    "male":{
        "salary_ranges":["0-7500","7501-10000","10000-x"],
        "tax_value":[0,175,200]
    },
    "female":{
        "salary_ranges":["0-7500","7501-10000","10000-x"],
        "tax_value":[0,175,200]
    },
    "exception":{
        "month":["2"],
        "value":[300]
    }  
},
  "West Bengal": {
    "base":"monthly",
    "male":{
        "salary_ranges":["0-10000","10001-15000","15000-25000","25001-40000","40001-x"],
        "tax_value":[0,110,130,150,200]
    },
    "female":{
        "salary_ranges":["0-10000","10001-15000","15000-25000","25001-40000","40001-x"],
        "tax_value":[0,110,130,150,200]
    },
    "exception":{
        "month":[],
        "value":[]
    }
}
}