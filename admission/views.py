import datetime
import io
import os
import random
from math import ceil

from PyPDF2 import PdfReader, PdfWriter
from django.http import HttpResponseRedirect, FileResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from xpinyin import Pinyin

from admission.models import Student
from collegefair.settings import BASE_DIR


def index(request):
    return render(request, './index.html')


@csrf_exempt
def add(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name == '':
            return render(request, './index.html', {'error': 'Please enter a name'})

        student = Student(name=name)
        student.save()
        return HttpResponseRedirect(reverse('admit_success'))


def admit_success(request):
    return render(request, '../templates/admit_success.html')


def result(request):
    if not request.user.is_superuser:
        return HttpResponseRedirect(reverse('index'))
    i = 1
    for student in Student.objects.all():
        Student.objects.filter(id=student.id).update(state=False)
        Student.objects.filter(id=student.id).update(id=i)
        i += 1
    random_list: list = random.sample(range(1, Student.objects.count() + 1), ceil(Student.objects.count() * 0.1))
    for j in random_list:
        Student.objects.filter(id=j).update(state=True)
    if request.GET.get('filter') == 'true':
        return render(request, '../templates/result.html', {'students': Student.objects.filter(state=True)})
    return render(request, './result.html', {'students': Student.objects.all()})


def get_certificate(request):
    if not request.user.is_superuser:
        return HttpResponseRedirect(reverse('index'))
    return redirect('/static/RejectionLetterLSE.pdf')


@csrf_exempt
def get_result(request):
    if request.method == 'GET':
        if datetime.datetime.now().timestamp() < datetime.datetime(2023, 4, 7, 14, 45, 0).timestamp():
            return render(request, '../templates/query.html', {'error': 'The result will be released at 14:45 on 7th '
                                                                        'April 2023', 'disabled': True})
        return render(request, '../templates/query.html')
    if request.method == 'POST':
        name = request.POST.get('name')
        if name == '':
            return render(request, '../templates/query.html', {'error': 'Please enter a name'})
        student = Student.objects.filter(name=name)
        if student.exists():
            if student.first().state:
                return FileResponse(generate_pdf(student_name=student.first().name, is_offer=True, x=76, y=535),
                                    content_type='application/pdf')
            else:
                return FileResponse(generate_pdf(student_name=student.first().name, is_offer=False, x=73, y=523),
                                    content_type='application/pdf')
        else:
            return render(request, '../templates/query.html', {'error': 'Student not found'})


def generate_pdf(student_name, is_offer, x, y):
    pdfmetrics.registerFont(TTFont('TimesNewRoman', os.path.join(BASE_DIR, 'static', 'TimesNewRoman.ttf')))
    packet = io.BytesIO()
    can = Canvas(packet, pagesize=A4)
    can.setFont('TimesNewRoman', 10)
    p = Pinyin()
    r = p.get_pinyin(student_name)
    s = r.split('-')
    can.drawString(x, y, ''.join(s[1:]).capitalize() + ' ' + s[0].capitalize() + ',')
    can.save()

    # move to the beginning of the StringIO buffer
    packet.seek(0)

    # create a new PDF with Reportlab
    new_pdf = PdfReader(packet)
    # read your existing PDF
    if is_offer:
        pdf = open(os.path.join(BASE_DIR, 'static/OfferLetterLSE.pdf'), 'rb')
    else:
        pdf = open(os.path.join(BASE_DIR, 'static/RejectionLetterLSE.pdf'), 'rb')
    pdf.seek(0)
    existing_pdf = PdfReader(pdf)
    output = PdfWriter()
    # add the "watermark" (which is the new pdf) on the existing page
    page = existing_pdf.pages[0]
    page.merge_page(new_pdf.pages[0])
    output.add_page(page)
    file = io.BytesIO()
    output.write(file)
    file.seek(0)
    return file
