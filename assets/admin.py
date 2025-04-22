from django.contrib import admin
from .models import Document, Classification, ClassificationCategory, ClassificationSkill, ClassificationDetail, Similarity

admin.site.register(Document)
admin.site.register(Classification)
admin.site.register(ClassificationCategory)
admin.site.register(ClassificationSkill)
admin.site.register(ClassificationDetail)
admin.site.register(Similarity)

