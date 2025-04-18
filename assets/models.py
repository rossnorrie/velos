from django.db import models
from django.utils import timezone

class asset(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    purchase_date = models.DateField()
    lease_status = models.BooleanField(default=False)
    price = models.FloatField(null=True, blank=True)
    datestamp = models.DateTimeField(default=timezone.now)
   

    def __str__(self):
        return self.name


class lease(models.Model):
    asset = models.ForeignKey(asset, on_delete=models.CASCADE)
    lessee_name = models.CharField(max_length=255)
    lease_start = models.DateField()
    lease_end = models.DateField()
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    datestamp = models.DateTimeField(default=timezone.now)
  

    def __str__(self):
        return f"Lease for {self.asset.name} by {self.lessee_name}"


class documentz(models.Model):
    id = models.AutoField(primary_key=True)
    file_name = models.CharField(max_length=255, null=True, blank=True)
    author = models.CharField(max_length=255, null=True, blank=True)
    created_date = models.DateTimeField(null=True, blank=True)
    text_contents = models.TextField(null=True, blank=True)
    image_hashes = models.TextField(null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    subject = models.CharField(max_length=255, null=True, blank=True)
    keywords = models.TextField(null=True, blank=True)
    last_modified_by = models.CharField(max_length=255, null=True, blank=True)
    revision = models.CharField(max_length=50, null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True)
    datestamp = models.DateTimeField(default=timezone.now)
  

    def __str__(self):
        return self.file_name or f"Documentz {self.id}"


class similarityz(models.Model):
    id = models.AutoField(primary_key=True)
    doc1_id = models.ForeignKey(documentz, related_name='sim_as_doc1', on_delete=models.SET_NULL, null=True, blank=True)
    doc2_id = models.ForeignKey(documentz, related_name='sim_as_doc2', on_delete=models.SET_NULL, null=True, blank=True)
    meta_sim = models.FloatField(null=True, blank=True)
    text_sim = models.FloatField(null=True, blank=True)
    image_sim = models.FloatField(null=True, blank=True)
    overall_sim = models.FloatField(null=True, blank=True)
    datestamp = models.DateTimeField(default=timezone.now)
  

    def __str__(self):
        return self.cat_name or f"similarityz {self.id}"
    
class report_categories(models.Model):
    cat_id = models.AutoField(primary_key=True)
    cat_name = models.CharField(max_length=255, null=True, blank=True)
    cat_description = models.CharField(max_length=512, null=True, blank=True)
    cat_icon = models.CharField(max_length=255, null=True, blank=True)
    datestamp = models.DateTimeField(default=timezone.now)
  

    def __str__(self):
        return self.cat_name or f"Category {self.cat_id}"


class reports(models.Model):
    report_id = models.AutoField(primary_key=True)
    cat_id = models.ForeignKey(report_categories, related_name='report_cat', on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    tree_items = models.CharField(max_length=512, null=True, blank=True)
    report_icon = models.CharField(max_length=255, null=True, blank=True)
    report_view = models.CharField(max_length=255, null=True, blank=True)
    report_image = models.CharField(max_length=255, null=True, blank=True)
    datestamp = models.DateTimeField(default=timezone.now)
  


    def __str__(self):
        return self.name or f"Report {self.report_id}"


class Document(models.Model):
    document_id = models.AutoField(primary_key=True)
    file_name = models.CharField(max_length=255, null=True, blank=True)
    file_path = models.CharField(max_length=1024, null=True, blank=True)
    extension = models.CharField(max_length=10, null=True, blank=True)
    md5 = models.CharField(max_length=32, null=True, blank=True)
    fs_props = models.TextField(null=True, blank=True)
    author = models.CharField(max_length=255, null=True, blank=True)
    created_date = models.DateTimeField(null=True, blank=True)
    text = models.TextField(null=True, blank=True)
    image_hashes = models.TextField(null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    subject = models.CharField(max_length=255, null=True, blank=True)
    keywords = models.TextField(null=True, blank=True)
    last_modified_by = models.CharField(max_length=255, null=True, blank=True)
    revision = models.CharField(max_length=50, null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True)
    datestamp = models.DateTimeField(default=timezone.now)
  

    def __str__(self):
        return self.file_name or f"Document {self.pk}"


class Classification(models.Model):
    document = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True, blank=True)
    datestamp = models.DateTimeField(default=timezone.now)
  

    def __str__(self):
        return f"Classification {self.pk} for Document {self.document_id}"


class ClassificationCategory(models.Model):
    classification = models.ForeignKey(Classification, on_delete=models.SET_NULL, null=True, blank=True)
    datestamp = models.DateTimeField(default=timezone.now)
  
    category = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.category or f"Category {self.pk}"


class ClassificationSkill(models.Model):
    classification = models.ForeignKey(Classification, on_delete=models.SET_NULL, null=True, blank=True)
    
    skill = models.CharField(max_length=255, null=True, blank=True)
    datestamp = models.DateTimeField(default=timezone.now)
  
    
    def __str__(self):
        return self.skill or f"Skill {self.pk}"


class ClassificationDetail(models.Model):
    classification = models.ForeignKey(Classification, on_delete=models.SET_NULL, null=True, blank=True)
    family = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True)
    skill = models.CharField(max_length=255, null=True, blank=True)
    frequency = models.IntegerField(null=True, blank=True)
    match_percentage = models.FloatField(null=True, blank=True)
    snippet = models.TextField(null=True, blank=True)
    datestamp = models.DateTimeField(default=timezone.now)
  

    def __str__(self):
        return f"{self.skill} ({self.match_percentage}%)" if self.skill else f"Detail {self.pk}"


class Similarity(models.Model):
    doc1 = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True, blank=True, related_name='similarity_doc1')
    doc2 = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True, blank=True, related_name='similarity_doc2')
    meta_sim = models.FloatField(null=True, blank=True)
    text_sim = models.FloatField(null=True, blank=True)
    image_sim = models.FloatField(null=True, blank=True)
    semantic_sim = models.FloatField(null=True, blank=True)
    overall_sim = models.FloatField(null=True, blank=True)
    datestamp = models.DateTimeField(default=timezone.now)
  

    def __str__(self):
        return f"Similarity {self.pk} - Doc {self.doc1_id} vs Doc {self.doc2_id}"
