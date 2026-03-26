# # from app.db.session import engine
# # from app.db.base import Base

# # # ✅ IMPORTANT: import all models
# # from app.models.user import User   # adjust path if needed

# # Base.metadata.drop_all(bind=engine)
# # Base.metadata.create_all(bind=engine)

# # print("Database reset complete!")

# def romanToInteger(s):
#     romans = {
#         'I': 1,
#         'V': 5,
#         'X': 10,
#         'L': 50,
#         'C': 100,
#         'D': 500,
#         'M': 1000
#     }
#     total = 0
    
#     for i in range(len(s)):
#         if i < len(s)-1 and romans[s[i]] < romans[s[i+1]]:
#             total = total - romans[s[i]]
#         else:
#             total = total + romans[s[i]]
            
#     return total

# s = 'III'
# res = romanToInteger(s)
# print(res)