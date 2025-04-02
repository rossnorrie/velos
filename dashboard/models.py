# Create your models here.
# dashboard/models.py
from django.db import models

class Asset(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    purchase_date = models.DateField()
    lease_status = models.BooleanField(default=False)
    # ... other fields

class Lease(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    lessee_name = models.CharField(max_length=255)
    lease_start = models.DateField()
    lease_end = models.DateField()
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    # ... other fields

class Documentz(models.Model):
    file_name = models.CharField(max_length=255, null=True, blank=True)
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

    def __str__(self):
        return self.title or self.file_name or f"Document {self.pk}"


class Similarityz(models.Model):
    doc1 = models.ForeignKey(Documentz, related_name='similarities_as_doc1', on_delete=models.SET_NULL, null=True, blank=True)
    doc2 = models.ForeignKey(Documentz, related_name='similarities_as_doc2', on_delete=models.SET_NULL, null=True, blank=True)
    meta_sim = models.FloatField(null=True, blank=True)
    text_sim = models.FloatField(null=True, blank=True)
    image_sim = models.FloatField(null=True, blank=True)
    overall_sim = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Similarity between {self.doc1} and {self.doc2}"